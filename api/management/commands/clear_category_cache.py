from django.core.management.base import BaseCommand
from api.models import CachedVenue


class Command(BaseCommand):
    help = 'Clear cached venues for a specific category'

    def add_arguments(self, parser):
        parser.add_argument('category', type=str, help='Category name to clear cache for')
        parser.add_argument('--all', action='store_true', help='Clear all cached venues')

    def handle(self, *args, **options):
        if options['all']:
            count = CachedVenue.objects.count()
            CachedVenue.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted ALL {count} cached venues'))
        else:
            category = options['category']
            queryset = CachedVenue.objects.filter(category=category)
            count = queryset.count()
            queryset.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {count} cached venues for "{category}"'))
