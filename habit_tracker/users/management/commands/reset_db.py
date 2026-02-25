from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Reset database: flush, migrate, populate challenges, create demo users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-demo', action='store_true',
            help='Skip creating demo users'
        )

    def handle(self, *args, **options):
        from django.core.management import call_command
        
        self.stdout.write(self.style.WARNING('⚠️  Flushing entire database...'))
        call_command('flush', '--noinput')
        self.stdout.write(self.style.SUCCESS('✅ Database flushed.'))
        
        self.stdout.write('📦 Running migrations...')
        call_command('migrate', '--noinput')
        self.stdout.write(self.style.SUCCESS('✅ Migrations applied.'))
        
        self.stdout.write('🎯 Populating challenges...')
        call_command('populate_challenges')
        self.stdout.write(self.style.SUCCESS('✅ Challenges populated.'))
        
        if not options['no_demo']:
            self.stdout.write('👥 Creating demo users...')
            call_command('create_demo_users')
            self.stdout.write(self.style.SUCCESS('✅ Demo users created.'))
        else:
            self.stdout.write('ℹ️  Skipping demo users (--no-demo flag)')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Database reset complete!'))
