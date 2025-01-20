from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    def handle(self, *args, **options):
        if connection:
            self.stdout.write('Successfully connected to the database\n')
        else:
            self.stdout.write('Failed to connect to the database\n')


if __name__ == '__main__':
    Command().handle(None, None)
