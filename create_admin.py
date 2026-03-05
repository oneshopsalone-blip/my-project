import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

# Create admin user
try:
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='Your-Very-Strong-Password-123!'
    )
    print("Admin user created successfully!")
except IntegrityError:
    print("Admin user already exists.")