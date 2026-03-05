"""
Custom management command to create a superuser with validation.
This provides a more secure and controlled way to create admin users.

Usage:
    python manage.py create_admin
    python manage.py create_admin --email admin@example.com --password SecurePass123!
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from getpass import getpass
import re
import sys
from typing import Optional

User = get_user_model()

# ============================================================================
# Validation Constants
# ============================================================================

PASSWORD_MIN_LENGTH = 12
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PASSWORD_REGEX = re.compile(
    r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).+$'
)


# ============================================================================
# Custom Command
# ============================================================================

class Command(BaseCommand):
    """
    Create a superuser with proper validation and security checks.
    
    This command extends Django's createsuperuser with additional
    validation for password strength and email format.
    """
    
    help = 'Create a superuser with proper validation and security checks'
    
    def add_arguments(self, parser):
        """Define command arguments"""
        parser.add_argument(
            '--email',
            type=str,
            help='Admin email address'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Admin password (will be prompted if not provided)'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            dest='first_name',
            help='First name'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            dest='last_name',
            help='Last name'
        )
        parser.add_argument(
            '--noinput',
            '--no-input',
            action='store_false',
            dest='interactive',
            help='Do NOT prompt the user for input of any kind'
        )
        parser.add_argument(
            '--skip-checks',
            action='store_true',
            help='Skip validation checks (use with caution)'
        )
    
    def handle(self, *args, **options):
        """
        Execute the command.
        """
        self.stdout.write(self.style.NOTICE(
            "\n🔐 Create Admin Superuser\n"
            "==========================\n"
        ))
        
        email = options.get('email')
        password = options.get('password')
        first_name = options.get('first_name')
        last_name = options.get('last_name')
        interactive = options.get('interactive', True)
        skip_checks = options.get('skip_checks', False)
        
        try:
            # Collect and validate user data
            user_data = self._collect_user_data(
                email, password, first_name, last_name, 
                interactive, skip_checks
            )
            
            # Create the superuser
            user = self._create_superuser(user_data)
            
            # Success message
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Superuser created successfully!\n"
                f"   Email: {user.email}\n"
                f"   Name: {user.get_full_name() or 'Not provided'}\n"
                f"   User ID: {user.user_id}\n"
                f"   Created: {user.date_joined.strftime('%Y-%m-%d %H:%M')}\n"
            ))
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("\n❌ Operation cancelled."))
            sys.exit(1)
        except Exception as e:
            raise CommandError(f"Failed to create superuser: {str(e)}")
    
    def _collect_user_data(self, email, password, first_name, last_name, 
                          interactive, skip_checks):
        """
        Collect and validate user input.
        """
        user_data = {}
        
        # Collect email
        user_data['email'] = self._get_email(email, interactive, skip_checks)
        
        # Check if user exists
        if User.objects.filter(email=user_data['email']).exists():
            raise CommandError(
                f"User with email '{user_data['email']}' already exists."
            )
        
        # Collect names
        user_data['first_name'] = self._get_input(
            first_name, "First name", interactive, default=""
        )
        user_data['last_name'] = self._get_input(
            last_name, "Last name", interactive, default=""
        )
        
        # Collect password
        user_data['password'] = self._get_password(
            password, interactive, skip_checks
        )
        
        return user_data
    
    def _get_email(self, email, interactive, skip_checks):
        """Get and validate email address"""
        if not email and interactive:
            while True:
                email = input("Email: ").strip().lower()
                if self._validate_email(email, skip_checks):
                    break
        elif email and not self._validate_email(email, skip_checks):
            raise CommandError(f"Invalid email format: {email}")
        
        if not email:
            raise CommandError("Email is required.")
        
        return email
    
    def _validate_email(self, email, skip_checks):
        """Validate email format"""
        if not email:
            self.stdout.write(self.style.ERROR("Email cannot be empty."))
            return False
        
        if not skip_checks and not EMAIL_REGEX.match(email):
            self.stdout.write(self.style.ERROR(
                "Invalid email format. Please use a valid email address."
            ))
            return False
        
        return True
    
    def _get_password(self, password, interactive, skip_checks):
        """Get and validate password"""
        if not password and interactive:
            while True:
                password = getpass("Password: ")
                
                if not skip_checks:
                    # Validate password strength
                    is_valid, error = self._validate_password_strength(password)
                    if not is_valid:
                        self.stdout.write(self.style.ERROR(error))
                        continue
                
                password2 = getpass("Password (again): ")
                
                if password != password2:
                    self.stdout.write(self.style.ERROR("Passwords do not match."))
                    continue
                
                break
        elif password and not skip_checks:
            # Validate provided password
            is_valid, error = self._validate_password_strength(password)
            if not is_valid:
                raise CommandError(error)
        
        if not password:
            raise CommandError("Password is required.")
        
        return password
    
    def _validate_password_strength(self, password):
        """Validate password strength"""
        if len(password) < PASSWORD_MIN_LENGTH:
            return False, (
                f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
            )
        
        if not re.search(r'[A-Z]', password):
            return False, (
                "Password must contain at least one uppercase letter."
            )
        
        if not re.search(r'[a-z]', password):
            return False, (
                "Password must contain at least one lowercase letter."
            )
        
        if not re.search(r'[0-9]', password):
            return False, (
                "Password must contain at least one number."
            )
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, (
                "Password must contain at least one special character "
                "(!@#$%^&*(),.?\":{}|<>)."
            )
        
        return True, None
    
    def _get_input(self, value, prompt, interactive, default=None):
        """Get input from user or use provided value"""
        if not value and interactive:
            value = input(f"{prompt} [{default}]: ").strip()
            return value if value else default
        return value or default
    
    def _create_superuser(self, user_data):
        """Create the superuser with provided data"""
        try:
            user = User.objects.create_superuser(
                email=user_data['email'],
                password=user_data['password'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                username=user_data['email'].split('@')[0],  # Generate username from email
                is_active=True,
                is_staff=True,
                is_superuser=True,
            )
            
            # Log creation
            self.stdout.write(self.style.NOTICE(
                f"✓ Superuser account created with ID: {user.user_id}"
            ))
            
            return user
            
        except Exception as e:
            raise CommandError(f"Database error: {str(e)}")


# ============================================================================
# Additional Utility Commands
# ============================================================================

# You can add more commands here if needed, for example:

class CommandListAdmins(BaseCommand):
    """List all admin users"""
    help = 'List all superuser accounts'
    
    def handle(self, *args, **options):
        users = User.objects.filter(is_superuser=True)
        
        self.stdout.write(self.style.NOTICE(
            f"\n📋 Admin Users ({users.count()})\n"
            "==========================\n"
        ))
        
        for user in users:
            self.stdout.write(
                f"{user.user_id} | {user.email} | {user.get_full_name() or 'No name'}"
            )
        
        self.stdout.write("\n")


class CommandResetFailedLogins(BaseCommand):
    """Reset failed login attempts for a user"""
    help = 'Reset failed login attempts for a specific user'
    
    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email')
    
    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options['email'])
            user.failed_login_attempts = 0
            user.is_locked = False
            user.lockout_until = None
            user.save()
            
            self.stdout.write(self.style.SUCCESS(
                f"✓ Failed login attempts reset for {user.email}"
            ))
        except User.DoesNotExist:
            raise CommandError(f"User with email {options['email']} not found")