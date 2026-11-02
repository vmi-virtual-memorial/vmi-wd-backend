from django.test import SimpleTestCase

from .branches import BRANCH_ALIASES, Branch, _tokens, infer_branch


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
