from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Conflict, Person


def make_person(conflict, **kwargs):
    defaults = {'first_name': 'John', 'last_name': 'Doe', 'conflict': conflict}
    defaults.update(kwargs)
    return Person.objects.create(**defaults)


class ClassLetterTests(TestCase):
    def setUp(self):
        self.conflict = Conflict.objects.create(name='World War II', start_year=1941, end_year=1945)

    def clean_letter(self, letter):
        person = Person(first_name='A', last_name='B', conflict=self.conflict, class_letter=letter)
        person.full_clean()
        return person.class_letter

    def test_accepts_single_letter(self):
        self.assertEqual(self.clean_letter('M'), 'M')

    def test_accepts_two_letters(self):
        self.assertEqual(self.clean_letter('MS'), 'MS')

    def test_normalizes_case_and_whitespace(self):
        self.assertEqual(self.clean_letter('ms'), 'MS')
        self.assertEqual(self.clean_letter(' m'), 'M')

    def test_blank_allowed(self):
        self.assertEqual(self.clean_letter(''), '')

    def test_rejects_three_letters(self):
        with self.assertRaises(ValidationError):
            self.clean_letter('MSX')

    def test_rejects_non_letters(self):
        for bad in ['1', 'M1', 'M-', 'É']:
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                self.clean_letter(bad)

    def test_two_letters_persist(self):
        person = make_person(self.conflict, class_year=1956, class_letter='MS')
        person.refresh_from_db()
        self.assertEqual(person.class_letter, 'MS')


class ClassYearDisplayTests(TestCase):
    def setUp(self):
        self.conflict = Conflict.objects.create(name='Civil War', start_year=1861, end_year=1865)

    def display(self, year, letter=''):
        return Person(first_name='A', last_name='B', conflict=self.conflict,
                      class_year=year, class_letter=letter).class_year_display

    def test_1900s_abbreviated(self):
        self.assertEqual(self.display(1942), "'42")
        self.assertEqual(self.display(1900), "'00")
        self.assertEqual(self.display(1905), "'05")
        self.assertEqual(self.display(1999), "'99")

    def test_1800s_full_year(self):
        self.assertEqual(self.display(1842), '1842')
        self.assertEqual(self.display(1899), '1899')

    def test_2000s_full_year(self):
        self.assertEqual(self.display(2000), '2000')
        self.assertEqual(self.display(2005), '2005')

    def test_letter_appended(self):
        self.assertEqual(self.display(1956, 'M'), "'56M")
        self.assertEqual(self.display(1956, 'MS'), "'56MS")
        self.assertEqual(self.display(1862, 'MS'), '1862MS')

    def test_no_year(self):
        self.assertEqual(self.display(None), '')

    def test_full_display_name_and_str(self):
        old = make_person(self.conflict, first_name='John', last_name='Wise', rank='Capt', class_year=1862)
        new = make_person(self.conflict, first_name='Jane', last_name='Roe', class_year=1942, class_letter='MS')
        self.assertEqual(old.full_display_name, 'Capt John Wise 1862')
        self.assertEqual(str(old), 'John Wise 1862')
        self.assertEqual(new.full_display_name, "Jane Roe '42MS")
        self.assertEqual(str(new), "Jane Roe '42MS")


class PersonApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.conflict = Conflict.objects.create(name='Civil War', start_year=1861, end_year=1865)
        self.old = make_person(self.conflict, first_name='John', last_name='Wise', class_year=1862, class_letter='M')
        self.new = make_person(self.conflict, first_name='Jane', last_name='Roe', class_year=1942, class_letter='MS')

    def test_detail_returns_two_letter_class_and_display(self):
        data = self.client.get(f'/api/memorial/persons/{self.new.id}/').json()
        self.assertEqual(data['class_letter'], 'MS')
        self.assertEqual(data['full_display_name'], "Jane Roe '42MS")

    def test_1800s_display_not_abbreviated_in_api(self):
        data = self.client.get(f'/api/memorial/persons/{self.old.id}/').json()
        self.assertEqual(data['full_display_name'], 'John Wise 1862M')

    def test_index_includes_class_letter(self):
        data = self.client.get('/api/memorial/index/').json()
        casualties = {p['id']: p for p in data[0]['casualties']}
        self.assertEqual(casualties[self.new.id]['class_letter'], 'MS')
        self.assertEqual(casualties[self.old.id]['full_display_name'], 'John Wise 1862M')

    def test_search_returns_display_names(self):
        data = self.client.get('/api/memorial/persons/search/?q=Wise').json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['full_display_name'], 'John Wise 1862M')
