from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Creates a superuser non-interactively if it does not exist'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Admin email')
        parser.add_argument('--password', type=str, help='Admin password')
        parser.add_argument('--first_name', type=str, help='Admin first name', default='Admin')
        parser.add_argument('--last_name', type=str, help='Admin last name', default='Admin')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']

        if not email or not password:
            self.stdout.write(self.style.ERROR('You must provide --email and --password'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Superuser "{email}" already exists.'))
            return

        try:
            User.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser "{email}" was created successfully.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
