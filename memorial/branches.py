"""Service branch taxonomy and inference.

Branch is not entered as its own field historically; it is usually embedded in
``rank`` as a suffix ("Captain USMC", "Private CSA") and sometimes only implied
by ``unit`` ("7th Marines", "USS Cooper"). ``infer_branch`` only returns a
branch for unambiguous signals; everything else is left blank for an admin.
"""
import re

from django.db import models


class Branch(models.TextChoices):
    ARMY = 'ARMY', 'U.S. Army'
    ARMY_AIR = 'ARMY_AIR', 'U.S. Army Air Forces'
    AIR_FORCE = 'AIR_FORCE', 'U.S. Air Force'
    NAVY = 'NAVY', 'U.S. Navy'
    MARINES = 'MARINES', 'U.S. Marine Corps'
    COAST_GUARD = 'COAST_GUARD', 'U.S. Coast Guard'
    CSA = 'CSA', 'Confederate States Army'
    ALLIED = 'ALLIED', 'Allied & Foreign Service'
    CIVILIAN = 'CIVILIAN', 'Civilian'
    CADET = 'CADET', 'VMI Corps of Cadets'


# Extra words a visitor might type for each branch; shipped in the search index.
BRANCH_ALIASES = {
    Branch.ARMY: ['army', 'usa', 'us army', 'soldier'],
    Branch.ARMY_AIR: ['army air forces', 'army air corps', 'air corps', 'air service', 'usaaf', 'usaac', 'aaf'],
    Branch.AIR_FORCE: ['air force', 'usaf', 'airman'],
    Branch.NAVY: ['navy', 'naval', 'usn', 'usnr', 'sailor'],
    Branch.MARINES: ['marines', 'marine', 'marine corps', 'usmc', 'usmcr'],
    Branch.COAST_GUARD: ['coast guard', 'uscg'],
    Branch.CSA: ['confederate', 'confederacy', 'csa'],
    Branch.ALLIED: ['allied', 'foreign', 'raf', 'royal air force', 'rcaf', 'british', 'canadian',
                    'french', 'foreign legion', 'bef', 'lafayette escadrille'],
    Branch.CIVILIAN: ['civilian'],
    Branch.CADET: ['cadet', 'cadets', 'new market cadets'],
}

# Rank tokens, checked in priority order so e.g. a Navy corpsman serving with a
# Marine unit ("... USN", unit "1st Marine Division") stays Navy.
_RANK_TOKENS = [
    (Branch.MARINES, {'USMC', 'USMCR'}),
    (Branch.NAVY, {'USN', 'USNR'}),
    (Branch.COAST_GUARD, {'USCG'}),
    (Branch.ARMY_AIR, {'USAAF', 'USAAC', 'USAAS'}),
    (Branch.AIR_FORCE, {'USAF'}),
    (Branch.CSA, {'CSA'}),
    (Branch.ARMY, {'USA', 'USANG', 'AUS', 'ARNG'}),
    (Branch.ALLIED, {'RAF', 'RCAF', 'RAAF', 'RFC', 'BEF', 'ROYAL', 'FRENCH', 'BRITISH', 'CANADIAN',
                     'AUSTRALIAN', 'ESCADRILLE'}),
    (Branch.CIVILIAN, {'CIVILIAN'}),
]

# Unit signals are weaker than rank, so only words that cannot mean anything else.
# Deliberately absent: "Army" (Army of Northern Virginia is CSA), "Air Force"
# (Seventh Air Force is WWII AAF), state regiments (West Virginia units were Union),
# and bare "Royal" (Port Royal); allied services are checked first so "Royal Marines" is not USMC.
_UNIT_TOKENS = [
    (Branch.ALLIED, {'RAF', 'RCAF', 'RAAF', 'RFC', 'BEF', 'FRENCH', 'BRITISH', 'CANADIAN',
                     'AUSTRALIAN', 'ESCADRILLE'}),
    (Branch.MARINES, {'USMC', 'USMCR', 'MARINE', 'MARINES'}),
    (Branch.NAVY, {'USS', 'USN', 'USNR', 'NAVY', 'NAVAL'}),
    (Branch.COAST_GUARD, {'USCG'}),
    (Branch.CSA, {'CSA'}),
]

_NEW_MARKET_CADET = re.compile(r'\bNEW MARKET CADETS?\b')
_MERCHANT_MARINE = re.compile(r'\bMERCHANT MARINES?\b')
_ROYAL_SERVICE = re.compile(r'\bROYAL (AIR FORCE|NAVY|NAVAL|MARINES?|ARMY|FLYING CORPS)\b')


def _tokens(text):
    """Uppercase alphanumeric tokens, with dotted/spaced initialisms collapsed:
    "C.S.A." -> CSA, "B. E. F" -> BEF, "U.S.S. Maine" -> USS, MAINE."""
    parts = re.findall(r'[A-Z0-9]+', (text or '').upper())
    tokens, letters = [], ''
    for part in parts:
        if len(part) == 1 and part.isalpha():
            letters += part
            continue
        if letters:
            tokens.append(letters)
            letters = ''
        tokens.append(part)
    if letters:
        tokens.append(letters)
    return tokens


def _match(tokens, table):
    found = set(tokens)
    for branch, keys in table:
        if found & keys:
            return branch
    return ''


def infer_branch(rank, unit=''):
    """Best-effort branch from rank/unit text; '' when there is no unambiguous signal."""
    rank_upper = (rank or '').upper()
    unit_upper = (unit or '').upper()

    if _NEW_MARKET_CADET.search(rank_upper) or _NEW_MARKET_CADET.search(unit_upper):
        return Branch.CADET

    branch = _match(_tokens(rank), _RANK_TOKENS)
    if branch:
        return branch

    if _ROYAL_SERVICE.search(unit_upper):
        return Branch.ALLIED
    if _MERCHANT_MARINE.search(unit_upper):
        return ''
    return _match(_tokens(unit), _UNIT_TOKENS)
