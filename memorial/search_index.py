"""Compact, cacheable snapshot of everything the frontend search engine indexes.

The memorial is small (hundreds of people) and changes rarely, so the frontend
downloads this once and searches it in the browser (see the search-overhaul plan).
Field names follow the existing API serializers.
"""
from collections import Counter, defaultdict

from django.db.models import Count, Sum

from .branches import BRANCH_ALIASES, Branch, infer_branch
from .models import Award, Conflict, Person, PersonAward

INDEX_VERSION = 1

_PERSON_FIELDS = (
    'id', 'first_name', 'middle_name', 'last_name', 'suffix', 'rank', 'unit', 'branch',
    'class_year', 'class_letter', 'conflict_id', 'date_of_death', 'death_date_precision',
    'death_description', 'pdf_key',
)


def _death_date_display(date, precision):
    # Mirrors Person.death_date_display without instantiating models.
    if not date:
        return None
    if precision == 'year':
        return str(date.year)
    if precision == 'month':
        return date.strftime('%B %Y')
    return date.strftime('%B %d, %Y')


def build_search_index():
    conflicts = [
        {
            'id': c.id, 'name': c.name, 'start_year': c.start_year, 'end_year': c.end_year,
            'casualty_count': c.n,
        }
        # Explicit order: Meta.ordering is ignored on GROUP BY (aggregate) queries.
        for c in Conflict.objects.annotate(n=Count('casualties')).order_by('order', '-start_year')
    ]

    awards = [
        {
            'id': a.id, 'name': a.name, 'image_filename': a.image_filename,
            'recipient_count': a.n_recipients, 'total_awards_given': a.n_given or 0,
        }
        for a in Award.objects.annotate(
            n_recipients=Count('person_awards__person', distinct=True),
            n_given=Sum('person_awards__count'),
        ).order_by('order', 'name')
    ]

    awards_by_person = defaultdict(list)
    for person_id, award_id in PersonAward.objects.order_by(
        'person_id', 'award__order', 'award__name'
    ).values_list('person_id', 'award_id'):
        awards_by_person[person_id].append(award_id)

    people = []
    branch_counts = Counter()
    for p in Person.objects.order_by('last_name', 'first_name', 'id').values(*_PERSON_FIELDS):
        branch = p['branch'] or infer_branch(p['rank'], p['unit'])
        if branch:
            branch_counts[branch] += 1
        people.append({
            'id': p['id'],
            'first_name': p['first_name'],
            'middle_name': p['middle_name'],
            'last_name': p['last_name'],
            'suffix': p['suffix'],
            'rank': p['rank'],
            'unit': p['unit'],
            'branch': branch,
            'class_year': p['class_year'],
            'class_letter': p['class_letter'],
            'conflict': p['conflict_id'],
            'date_of_death': p['date_of_death'].isoformat() if p['date_of_death'] else None,
            'death_date_display': _death_date_display(p['date_of_death'], p['death_date_precision']),
            'death_description': p['death_description'],
            'has_document': bool(p['pdf_key']),
            'awards': awards_by_person.get(p['id'], []),
        })

    branches = [
        {'code': b.value, 'name': b.label, 'aliases': BRANCH_ALIASES[b], 'count': branch_counts[b]}
        for b in Branch
        if branch_counts[b]
    ]

    return {
        'version': INDEX_VERSION,
        'conflicts': conflicts,
        'awards': awards,
        'branches': branches,
        'people': people,
    }
