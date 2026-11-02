from unittest import mock

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from rest_framework.throttling import SimpleRateThrottle

from .models import Conflict, Contribution, Person
from .throttles import ContributionRateThrottle

LOW_RATES = {'anon': '3/hour', 'user': '100/hour', 'contribute': '2/hour'}


def contribution(**overrides):
    data = {'contributor_email': 'kin@example.com', 'content_type': 'text', 'content_text': 'Remembered.'}
    data.update(overrides)
    return data


class ThrottleSettingsTests(TestCase):
    def test_reads_are_generous_and_writes_strict(self):
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']

        def per_hour(rate):
            num, seconds = SimpleRateThrottle.parse_rate(None, rate)
            return num * 3600 / seconds

        self.assertGreaterEqual(per_hour(rates['anon']), 1000)
        self.assertLess(per_hour(rates['contribute']), per_hour(rates['anon']))


@mock.patch.object(SimpleRateThrottle, 'THROTTLE_RATES', LOW_RATES)
class ThrottleBehaviorTests(TestCase):
    def setUp(self):
        cache.clear()
        conflict = Conflict.objects.create(name='Korean War', start_year=1950, end_year=1953)
        self.person = Person.objects.create(first_name='A', last_name='B', conflict=conflict)
        self.contribute_url = f'/api/memorial/persons/{self.person.id}/contributions/'

    def tearDown(self):
        cache.clear()

    def test_anonymous_reads_throttled_at_anon_rate(self):
        codes = [self.client.get('/api/memorial/conflicts/').status_code for _ in range(4)]
        self.assertEqual(codes, [200, 200, 200, 429])

    def test_contributions_have_their_own_budget(self):
        first = self.client.post(self.contribute_url, contribution())
        second = self.client.post(self.contribute_url, contribution())
        third = self.client.post(self.contribute_url, contribution())
        self.assertEqual((first.status_code, second.status_code, third.status_code), (201, 201, 429))
        self.assertEqual(third.json(), {'error': 'Rate limit exceeded. Please try again later.'})
        self.assertGreater(int(third['Retry-After']), 0)
        self.assertEqual(Contribution.objects.count(), 2)

    def test_clients_counted_separately(self):
        for _ in range(2):
            self.client.post(self.contribute_url, contribution(), REMOTE_ADDR='10.0.0.1')
        blocked = self.client.post(self.contribute_url, contribution(), REMOTE_ADDR='10.0.0.1')
        other = self.client.post(self.contribute_url, contribution(), REMOTE_ADDR='10.0.0.2')
        self.assertEqual((blocked.status_code, other.status_code), (429, 201))


class ContributionThrottleKeyTests(TestCase):
    def test_key_by_ip_when_anonymous_and_by_user_when_logged_in(self):
        throttle = ContributionRateThrottle()
        request = RequestFactory().post('/', REMOTE_ADDR='10.1.2.3')
        request.user = AnonymousUser()
        self.assertEqual(throttle.get_cache_key(request, None), 'throttle_contribute_10.1.2.3')
        request.user = User.objects.create_user('kin', password='pw')
        self.assertEqual(throttle.get_cache_key(request, None), f'throttle_contribute_{request.user.pk}')
