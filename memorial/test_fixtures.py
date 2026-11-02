from django.test import TestCase

from .models import Person
from .search_index import build_search_index


class SearchDemoFixtureTests(TestCase):
    """The synthetic fixture backs frontend golden-query tests and full-stack e2e."""
    fixtures = ['search_demo']

    def test_loads_and_indexes(self):
        index = build_search_index()
        self.assertEqual(len(index['people']), Person.objects.count())
        self.assertEqual(len(index['people']), 40)
        self.assertEqual(len(index['conflicts']), 11)
        silver = next(a for a in index['awards'] if a['name'] == 'Silver Star')
        self.assertEqual((silver['recipient_count'], silver['total_awards_given']), (7, 8))
        branches = {b['code']: b['count'] for b in index['branches']}
        self.assertEqual(branches['MARINES'], 6)
        self.assertEqual(sum(branches.values()), 39)  # one person left unclassified on purpose
