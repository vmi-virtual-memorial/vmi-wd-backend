import gzip
import json
from datetime import date

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .branches import Branch
from .models import Award, Conflict, Person, PersonAward

URL = '/api/memorial/search-index/'


class SearchIndexTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Award.objects.all().delete()  # drop the awards seeded by migration 0008 to keep fixtures explicit
        cls.vietnam = Conflict.objects.create(name='Vietnam War', start_year=1955, end_year=1975, order=1)
        cls.civil = Conflict.objects.create(name='Civil War', start_year=1861, end_year=1865, order=2)
        cls.silver = Award.objects.create(name='Silver Star', short_description='s', long_description='l', order=7)
        cls.medaille = Award.objects.create(name='Médaille Militaire', short_description='s', long_description='l',
                                            image_filename='MedailleMilitaire', order=9)
        cls.dsc = Award.objects.create(name='Distinguished Service Cross', short_description='s',
                                       long_description='l', order=4)
        cls.doe = Person.objects.create(
            first_name='John', middle_name='Allen', last_name='Doe', suffix='Jr.', rank='Captain USMC',
            unit='Company C, 1st Battalion, 7th Marines, 1st Marine Division', class_year=1966,
            conflict=cls.vietnam, date_of_death=date(1968, 3, 1), death_date_precision='month',
            death_description='Awarded the Silver Star near Hué.', pdf_key='prod/memorials/doe.pdf',
        )
        cls.roe = Person.objects.create(
            first_name='Richard', last_name='Roe', rank='Private', branch=Branch.ARMY,
            class_year=1862, class_letter='M', conflict=cls.civil,
        )
        cls.unknown = Person.objects.create(first_name='Ann', last_name='Able', conflict=cls.civil)
        PersonAward.objects.create(person=cls.doe, award=cls.silver, count=2)
        PersonAward.objects.create(person=cls.doe, award=cls.dsc)

    def get(self, **headers):
        return self.client.get(URL, **headers)

    def test_people(self):
        people = {p['id']: p for p in self.get().json()['people']}
        doe = people[self.doe.id]
        self.assertEqual(doe, {
            'id': self.doe.id,
            'first_name': 'John', 'middle_name': 'Allen', 'last_name': 'Doe', 'suffix': 'Jr.',
            'rank': 'Captain USMC', 'unit': 'Company C, 1st Battalion, 7th Marines, 1st Marine Division',
            'branch': 'MARINES', 'class_year': 1966, 'class_letter': '', 'conflict': self.vietnam.id,
            'date_of_death': '1968-03-01', 'death_date_display': 'March 1968',
            'death_description': 'Awarded the Silver Star near Hué.', 'has_document': True,
            'awards': [self.dsc.id, self.silver.id],
        })
        self.assertNotIn('pdf_key', doe)
        self.assertEqual(people[self.roe.id]['branch'], 'ARMY')
        self.assertEqual(people[self.unknown.id]['branch'], '')
        self.assertIsNone(people[self.unknown.id]['date_of_death'])
        self.assertIsNone(people[self.unknown.id]['death_date_display'])
        self.assertFalse(people[self.unknown.id]['has_document'])

    def test_people_sorted_by_name(self):
        names = [p['last_name'] for p in self.get().json()['people']]
        self.assertEqual(names, ['Able', 'Doe', 'Roe'])

    def test_death_date_display_matches_model(self):
        people = {p['id']: p for p in self.get().json()['people']}
        for precision in ('day', 'month', 'year'):
            Person.objects.filter(pk=self.doe.pk).update(death_date_precision=precision)
            self.doe.refresh_from_db()
            people = {p['id']: p for p in self.get().json()['people']}
            with self.subTest(precision=precision):
                self.assertEqual(people[self.doe.id]['death_date_display'], self.doe.death_date_display)

    def test_conflicts_awards_branches(self):
        data = self.get().json()
        self.assertEqual(data['version'], 1)
        self.assertEqual(
            [(c['name'], c['casualty_count']) for c in data['conflicts']],
            [('Vietnam War', 1), ('Civil War', 2)],
        )
        awards = {a['name']: a for a in data['awards']}
        self.assertEqual([a['name'] for a in data['awards']],
                         ['Distinguished Service Cross', 'Silver Star', 'Médaille Militaire'])
        self.assertEqual((awards['Silver Star']['recipient_count'], awards['Silver Star']['total_awards_given']), (1, 2))
        self.assertEqual((awards['Médaille Militaire']['recipient_count'],
                          awards['Médaille Militaire']['total_awards_given']), (0, 0))
        self.assertEqual(awards['Médaille Militaire']['image_filename'], 'MedailleMilitaire')
        self.assertEqual(
            [(b['code'], b['name'], b['count']) for b in data['branches']],
            [('ARMY', 'U.S. Army', 1), ('MARINES', 'U.S. Marine Corps', 1)],
        )
        self.assertIn('marines', data['branches'][1]['aliases'])

    def test_query_count_is_constant(self):
        with CaptureQueriesContext(connection) as before:
            self.get()
        for i in range(10):
            Person.objects.create(first_name='X', last_name=f'Extra{i}', rank='Private CSA', conflict=self.civil)
        with CaptureQueriesContext(connection) as after:
            self.get()
        self.assertEqual(len(before), 4)
        self.assertEqual(len(after), 4)

    def test_unicode_not_escaped(self):
        self.assertIn('Médaille'.encode(), self.get().content)

    def test_cache_headers(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json; charset=utf-8')
        cache = response['Cache-Control']
        for part in ('public', 'max-age=300', 'stale-while-revalidate=86400'):
            self.assertIn(part, cache)

    def test_etag_revalidation(self):
        etag = self.get()['ETag']
        self.assertTrue(etag.startswith('"'))
        for sent in (etag, f'W/{etag}'):
            with self.subTest(sent=sent):
                response = self.get(HTTP_IF_NONE_MATCH=sent)
                self.assertEqual(response.status_code, 304)
                self.assertEqual(response.content, b'')
                self.assertIn('max-age=300', response['Cache-Control'])
        self.assertEqual(self.get(HTTP_IF_NONE_MATCH='"stale"').status_code, 200)

    def test_etag_changes_with_data(self):
        etag = self.get()['ETag']
        PersonAward.objects.create(person=self.roe, award=self.medaille)
        response = self.get(HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response['ETag'], etag)

    def test_gzip(self):
        plain = self.get().content
        response = self.get(HTTP_ACCEPT_ENCODING='gzip')
        self.assertEqual(response['Content-Encoding'], 'gzip')
        self.assertEqual(gzip.decompress(response.content), plain)
        # Compressed responses carry a weak ETag that still revalidates.
        self.assertEqual(self.get(HTTP_IF_NONE_MATCH=response['ETag']).status_code, 304)

    def test_read_only(self):
        # Anonymous writes hit DRF's permission check (403) before method dispatch (405).
        self.assertIn(self.client.post(URL).status_code, (403, 405))

    def test_empty_database(self):
        Person.objects.all().delete()
        Conflict.objects.all().delete()
        Award.objects.all().delete()
        data = self.get().json()
        self.assertEqual((data['people'], data['conflicts'], data['awards'], data['branches']), ([], [], [], []))

    def test_payload_is_compact_json(self):
        body = self.get().content.decode()
        self.assertNotIn(', ', body.replace('Company C, 1st', '').replace('Battalion, 7th', '')
                         .replace('Marines, 1st', ''))
        json.loads(body)
