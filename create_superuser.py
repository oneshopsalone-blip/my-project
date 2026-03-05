import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Create superuser if it doesn't exist
email = "admin@example.com"  # Change to your email
password = "Mysecurep@ssw0rd"  # Change to your password

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print(f"Superuser {email} created successfully!")
else:
    print(f"Superuser {email} already exists.")