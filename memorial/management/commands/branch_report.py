import csv

from django.core.management.base import BaseCommand

from memorial.branches import Branch, infer_branch
from memorial.models import Person


class Command(BaseCommand):
    help = (
        "Read-only report of where each person's service branch comes from "
        "(set manually, inferred from rank/unit, or unclassified). Never writes data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--list', choices=['missing', 'inferred', 'none'], default='missing',
            help='Which people to list after the summary (default: missing)',
        )
        parser.add_argument('--csv', action='store_true', help='Emit the list as CSV (no summary)')

    def handle(self, *args, **options):
        rows = []
        for person in Person.objects.select_related('conflict').order_by('last_name', 'first_name'):
            inferred = infer_branch(person.rank, person.unit)
            source = 'set' if person.branch else ('inferred' if inferred else 'missing')
            rows.append((person, source, person.branch or inferred))

        listed = [r for r in rows if r[1] == options['list']]

        if options['csv']:
            writer = csv.writer(self.stdout)
            writer.writerow(['id', 'name', 'conflict', 'rank', 'unit', 'source', 'branch'])
            for person, source, branch in listed:
                writer.writerow([person.id, person.display_name, person.conflict.name,
                                 person.rank, person.unit, source, branch])
            return

        by_source = {s: sum(1 for r in rows if r[1] == s) for s in ('set', 'inferred', 'missing')}
        self.stdout.write(
            f"{len(rows)} people: {by_source['set']} set manually, "
            f"{by_source['inferred']} inferred, {by_source['missing']} unclassified"
        )
        for branch in Branch:
            count = sum(1 for r in rows if r[2] == branch)
            if count:
                self.stdout.write(f"  {branch.label}: {count}")

        if listed:
            self.stdout.write(f"\n{options['list'].capitalize()} ({len(listed)}):")
            for person, _, branch in listed:
                suffix = f" -> {Branch(branch).label}" if branch else ''
                self.stdout.write(
                    f"  #{person.id} {person.display_name} [{person.conflict.name}] "
                    f"rank={person.rank!r} unit={person.unit!r}{suffix}"
                )
