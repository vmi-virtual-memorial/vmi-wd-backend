from datetime import date

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from .branches import Branch
from .models import Award, Conflict, Person, PersonAward

URL = '/api/memorial/persons/search/'


class PersonSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vietnam = Conflict.objects.create(name='Vietnam War', start_year=1955, end_year=1975)
        cls.civil = Conflict.objects.create(name='Civil War', start_year=1861, end_year=1865)
        cls.silver = Award.objects.get(name='Silver Star')  # seeded by migration 0008
        cls.dsc = Award.objects.get(name='Distinguished Service Cross')
        make = lambda **kw: Person.objects.create(**kw)
        cls.doe = make(first_name='John', middle_name='Allen', last_name='Doe', rank='Captain USMC',
                       unit='Company C, 1st Battalion, 7th Marines', class_year=1966, conflict=cls.vietnam,
                       death_description='Killed near Hue while leading a patrol.', pdf_key='x.pdf',
                       date_of_death=date(1968, 2, 1))
        cls.roe = make(first_name='Richard', last_name='Roe', rank='Private', unit='19th Virginia Infantry',
                       branch=Branch.CSA, class_year=1862, class_letter='M', conflict=cls.civil,
                       death_description='Mortally wounded at Gettysburg.')
        cls.poe = make(first_name='Edgar', last_name='Poe', rank='First Lieutenant USA',
                       unit='7th Cavalry', class_year=1967, conflict=cls.vietnam)
        PersonAward.objects.create(person=cls.doe, award=cls.silver)
        PersonAward.objects.create(person=cls.poe, award=cls.dsc)

    def setUp(self):
        self.client = APIClient()

    def ids(self, query):
        data = self.client.get(f'{URL}?{query}').json()
        self.assertEqual(data['count'], len(data['results']))
        return {p['id'] for p in data['results']}

    def test_no_filters_returns_everyone(self):
        self.assertEqual(self.ids(''), {self.doe.id, self.roe.id, self.poe.id})

    def test_multi_word_name(self):
        self.assertEqual(self.ids('q=John Doe'), {self.doe.id})
        self.assertEqual(self.ids('q=john allen doe'), {self.doe.id})
        self.assertEqual(self.ids('q=John Roe'), set())

    def test_scope_defaults_to_names(self):
        self.assertEqual(self.ids('q=Gettysburg'), set())
        self.assertEqual(self.ids('q=Gettysburg&in=cod'), {self.roe.id})
        self.assertEqual(self.ids('q=Gettysburg&in=bogus'), set())

    def test_scopes_combine(self):
        self.assertEqual(self.ids('q=7th&in=unit'), {self.doe.id, self.poe.id})
        self.assertEqual(self.ids('q=doe 7th&in=name,unit'), {self.doe.id})
        self.assertEqual(self.ids('q=lieutenant&in=rank'), {self.poe.id})

    def test_branch_uses_effective_branch(self):
        self.assertEqual(self.ids('branch=MARINES'), {self.doe.id})   # inferred from rank
        self.assertEqual(self.ids('branch=CSA'), {self.roe.id})       # stored override
        self.assertEqual(self.ids('branch=MARINES,ARMY'), {self.doe.id, self.poe.id})
        self.assertEqual(self.ids('branch=NOPE'), {self.doe.id, self.roe.id, self.poe.id})

    def test_award_filters(self):
        self.assertEqual(self.ids(f'award={self.silver.id}'), {self.doe.id})
        self.assertEqual(self.ids(f'award={self.silver.id},{self.dsc.id}'), {self.doe.id, self.poe.id})
        self.assertEqual(self.ids('award=any'), {self.doe.id, self.poe.id})
        self.assertEqual(self.ids('has_awards=true'), {self.doe.id, self.poe.id})

    def test_unit_and_rank_contains(self):
        self.assertEqual(self.ids('unit=1st battalion, 7th marines'), {self.doe.id})
        self.assertEqual(self.ids('rank=usmc'), {self.doe.id})

    def test_class_year_range(self):
        self.assertEqual(self.ids('class_year_from=1900'), {self.doe.id, self.poe.id})
        self.assertEqual(self.ids('class_year_from=1960&class_year_to=1966'), {self.doe.id})
        self.assertEqual(self.ids('class_year_to=x'), {self.doe.id, self.roe.id, self.poe.id})

    def test_existing_filters_still_work(self):
        self.assertEqual(self.ids(f'conflict={self.civil.id}'), {self.roe.id})
        self.assertEqual(self.ids('class_year=1862,1967'), {self.roe.id, self.poe.id})
        self.assertEqual(self.ids('has_document=true'), {self.doe.id})
        self.assertEqual(self.ids('no_date=true'), {self.roe.id, self.poe.id})

    def test_filters_combine(self):
        self.assertEqual(self.ids(f'conflict={self.vietnam.id}&award=any&branch=ARMY'), {self.poe.id})

    def test_result_fields(self):
        results = {p['id']: p for p in self.client.get(URL).json()['results']}
        self.assertEqual(results[self.doe.id]['branch'], 'MARINES')
        self.assertTrue(results[self.doe.id]['has_awards'])
        self.assertEqual(results[self.roe.id]['branch'], 'CSA')
        self.assertFalse(results[self.roe.id]['has_awards'])
        self.assertEqual(results[self.doe.id]['conflict_name'], 'Vietnam War')

    def test_no_per_row_queries(self):
        with CaptureQueriesContext(connection) as small:
            self.client.get(URL)
        for i in range(10):
            Person.objects.create(first_name='X', last_name=f'Extra{i}', conflict=self.civil)
        with CaptureQueriesContext(connection) as large:
            self.client.get(URL)
        self.assertEqual(len(small), len(large))
        self.assertEqual(len(large), 1)
