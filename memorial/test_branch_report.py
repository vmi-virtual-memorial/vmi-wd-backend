import csv
import io

from django.core.management import call_command
from django.test import TestCase

from .branches import Branch
from .models import Conflict, Person


class BranchReportCommandTests(TestCase):
    def setUp(self):
        conflict = Conflict.objects.create(name='Civil War', start_year=1861, end_year=1865)
        make = lambda last, **kw: Person.objects.create(first_name='A', last_name=last, conflict=conflict, **kw)
        self.manual = make('Manual', rank='Private', branch=Branch.CSA)
        self.inferred = make('Inferred', rank='Captain CSA')
        self.missing = make('Missing', rank='Private', unit='19th Virginia Infantry')

    def run_report(self, *args):
        out = io.StringIO()
        call_command('branch_report', *args, stdout=out)
        return out.getvalue()

    def test_summary_and_missing_list(self):
        out = self.run_report()
        self.assertIn('3 people: 1 set manually, 1 inferred, 1 unclassified', out)
        self.assertIn('Confederate States Army: 2', out)
        self.assertIn(f'#{self.missing.id}', out)
        self.assertNotIn(f'#{self.inferred.id}', out)

    def test_inferred_list_shows_guess(self):
        out = self.run_report('--list', 'inferred')
        self.assertIn(f'#{self.inferred.id}', out)
        self.assertIn('-> Confederate States Army', out)

    def test_list_none(self):
        out = self.run_report('--list', 'none')
        self.assertNotIn('#', out)

    def test_csv(self):
        rows = list(csv.reader(io.StringIO(self.run_report('--csv'))))
        self.assertEqual(rows[0], ['id', 'name', 'conflict', 'rank', 'unit', 'source', 'branch'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(self.missing.id))
        self.assertEqual(rows[1][5], 'missing')

    def test_is_read_only(self):
        before = list(Person.objects.order_by('id').values_list('branch', 'updated_at'))
        self.run_report('--list', 'inferred')
        self.run_report('--csv')
        after = list(Person.objects.order_by('id').values_list('branch', 'updated_at'))
        self.assertEqual(before, after)
