from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from .admin import PersonAdmin
from .branches import BRANCH_ALIASES, Branch, _tokens, infer_branch
from .models import Conflict, Person


class TokenTests(SimpleTestCase):
    def test_collapses_dotted_initialisms(self):
        self.assertEqual(_tokens('C.S.A.'), ['CSA'])
        self.assertEqual(_tokens('B. E. F'), ['BEF'])
        self.assertEqual(_tokens('U.S.S. Maine'), ['USS', 'MAINE'])
        self.assertEqual(_tokens('Lieutenant, USN/C&GS'), ['LIEUTENANT', 'USN', 'C', 'GS'])

    def test_empty(self):
        self.assertEqual(_tokens(''), [])
        self.assertEqual(_tokens(None), [])


class InferFromRankTests(SimpleTestCase):
    """Rank strings as they appear in the memorial data."""

    CASES = [
        ('First Lieutenant USA', Branch.ARMY),
        ('1st Lieutenant USA', Branch.ARMY),
        ('Captain USA Retired', Branch.ARMY),
        ('Captain USANG', Branch.ARMY),
        ('Private CSA', Branch.CSA),
        ("First Lieutenant, Cutshaw's Battery, C.S.A.", Branch.CSA),
        ('First Lieutenant USAAF', Branch.ARMY_AIR),
        ('Captain USAAC', Branch.ARMY_AIR),
        ('Captain USAF', Branch.AIR_FORCE),
        ('Captain USMC', Branch.MARINES),
        ('USMC Retired', Branch.MARINES),
        ('Lieutenant USN', Branch.NAVY),
        ('Lieutenant, USN', Branch.NAVY),
        ('USN Retired', Branch.NAVY),
        ('Ensign USNR', Branch.NAVY),
        ('Lieutenant, USN/C&GS', Branch.NAVY),
        ('Pharmacist Mate, 2nd Class, USN A.E.F.', Branch.NAVY),
        ('First Officer RAF ATA', Branch.ALLIED),
        ('First Lieutenant B.E.F.', Branch.ALLIED),
        ('Second Lieutenant, B.E.F.', Branch.ALLIED),
        ('Corporal French Foreign Legion', Branch.ALLIED),
        ('Private, French Foreign Legion', Branch.ALLIED),
        ('Sergeant French Air Force', Branch.ALLIED),
        ('Warrent Officer First Class Royal Canadian Air Force', Branch.ALLIED),
        ('Pilot Officer Roal Australian Air Force', Branch.ALLIED),
        ('Civilian', Branch.CIVILIAN),
        ('New Market Cadet', Branch.CADET),
    ]

    UNKNOWN = [
        '', 'Private', 'Captain', 'Sergeant Major', 'Private Company B', 'Corporal Company A',
        'First Lieutenant, Surgeon', 'Aviation Cadet', 'Leading Air Cadet', 'Courier', 'Volunteer',
        'Field Clerk', 'Assistant Adjutant General', 'Air Pilot', 'Petty Officer Second Class',
        'Yeoman, 3rd Class', 'Lieutenant Junior Grade',
    ]

    def test_known(self):
        for rank, expected in self.CASES:
            with self.subTest(rank=rank):
                self.assertEqual(infer_branch(rank), expected)

    def test_unknown_is_blank(self):
        for rank in self.UNKNOWN:
            with self.subTest(rank=rank):
                self.assertEqual(infer_branch(rank), '')

    def test_none_safe(self):
        self.assertEqual(infer_branch(None, None), '')

    def test_suffix_must_be_whole_token(self):
        self.assertEqual(infer_branch('Captain USAFR-ish'), '')
        self.assertEqual(infer_branch('Lieutenant Usher'), '')


class InferFromUnitTests(SimpleTestCase):
    CASES = [
        ('Company C, 1st Battalion, 7th Marines, 1st Marine Division', Branch.MARINES),
        ('Headquarters, 4th Regiment, U. S. Marines, Santiago, D. R.', Branch.MARINES),
        ('USMC Department of the Pacific', Branch.MARINES),
        ('USS Cooper DD-695', Branch.NAVY),
        ('USS Liscome Bay  (CVE-56)', Branch.NAVY),
        ('USNR', Branch.NAVY),
        ('Royal Air Force, B.E.F.', Branch.ALLIED),
        ('Royal Canadian Air Force', Branch.ALLIED),
        ('419th RCAF Moose Squadron', Branch.ALLIED),
        ('13th Demi-Brigade, French Foreign Legion', Branch.ALLIED),
        ('N 124 Lafayette Escadrille', Branch.ALLIED),
        ('Canadian Army', Branch.ALLIED),
        ('42 Commando, Royal Marines', Branch.ALLIED),
        ('New Market Cadets', Branch.CADET),
    ]

    UNKNOWN = [
        '4th West Virginia Infantry Regiment',
        '19th Virginia Infantry',
        'Company K, 7th Virginia Cavalry Regiment',
        '10th Army',
        'General Staff, Seventh Army',
        'Coast & Geodetic Survey Philippines',
        '557th Tactical Fighter Squadron',
        'Medical Corps, 41st Division, 164th Field Hospital, A.E.F.',
        'Battery at Port Royal',
        'SS Cedar Mills, Merchant Marine',
        '1st Submarine Squadron',
    ]

    def test_known(self):
        for unit, expected in self.CASES:
            with self.subTest(unit=unit):
                self.assertEqual(infer_branch('', unit), expected)

    def test_unknown_is_blank(self):
        for unit in self.UNKNOWN:
            with self.subTest(unit=unit):
                self.assertEqual(infer_branch('', unit), '')

    def test_rank_beats_unit(self):
        # Navy corpsman attached to a Marine division stays Navy.
        self.assertEqual(infer_branch('Pharmacist Mate USN', '1st Marine Division'), Branch.NAVY)

    def test_unit_used_when_rank_is_bare(self):
        self.assertEqual(infer_branch('Corporal', 'Company H, 3rd Battalion, 5th Marines'), Branch.MARINES)


class AliasTests(SimpleTestCase):
    def test_every_branch_has_aliases(self):
        self.assertEqual(set(BRANCH_ALIASES), set(Branch))
        for branch, aliases in BRANCH_ALIASES.items():
            with self.subTest(branch=branch):
                self.assertTrue(aliases)
                self.assertTrue(all(a == a.lower() for a in aliases))


class EffectiveBranchTests(TestCase):
    def setUp(self):
        self.conflict = Conflict.objects.create(name='World War II', start_year=1941, end_year=1945)

    def person(self, **kwargs):
        return Person.objects.create(first_name='A', last_name='B', conflict=self.conflict, **kwargs)

    def test_defaults_blank_and_inferred(self):
        person = self.person(rank='Captain USMC')
        self.assertEqual(person.branch, '')
        self.assertEqual(person.effective_branch, Branch.MARINES)

    def test_stored_branch_overrides_inference(self):
        person = self.person(rank='Captain USA', branch=Branch.ARMY_AIR)
        self.assertEqual(person.effective_branch, Branch.ARMY_AIR)

    def test_unknown_stays_blank(self):
        self.assertEqual(self.person(rank='Private').effective_branch, '')

    def test_invalid_choice_rejected(self):
        person = Person(first_name='A', last_name='B', conflict=self.conflict, branch='SPACE')
        with self.assertRaises(ValidationError):
            person.full_clean()


class BranchAdminTests(TestCase):
    def setUp(self):
        conflict = Conflict.objects.create(name='Vietnam War', start_year=1955, end_year=1975)
        make = lambda last, **kw: Person.objects.create(first_name='A', last_name=last, conflict=conflict, **kw)
        self.manual = make('Manual', rank='Captain', branch=Branch.NAVY)
        self.inferred = make('Inferred', rank='Captain USMC')
        self.missing = make('Missing', rank='Private')
        user = User.objects.create_superuser('admin', 'admin@example.com', 'pw')
        self.client.force_login(user)

    def changelist(self, query=''):
        response = self.client.get(f'/admin/memorial/person/{query}')
        self.assertEqual(response.status_code, 200)
        return {p.id for p in response.context['cl'].queryset}

    def test_status_filter(self):
        self.assertEqual(self.changelist('?branch_status=set'), {self.manual.id})
        self.assertEqual(self.changelist('?branch_status=inferred'), {self.inferred.id})
        self.assertEqual(self.changelist('?branch_status=missing'), {self.missing.id})
        self.assertEqual(len(self.changelist()), 3)

    def test_branch_column_marks_inferred(self):
        admin = PersonAdmin(Person, AdminSite())
        self.assertEqual(admin.get_branch(self.manual), 'U.S. Navy')
        self.assertIn('(inferred)', admin.get_branch(self.inferred))
        self.assertIn('U.S. Marine Corps', admin.get_branch(self.inferred))
        self.assertEqual(admin.get_branch(self.missing), '—')

    def test_change_form_has_branch_field(self):
        response = self.client.get(f'/admin/memorial/person/{self.inferred.id}/change/')
        self.assertContains(response, 'name="branch"')
