"""
Account management models for We Yone Pot - Digital Osusu Platform
Handles user authentication, profiles, and activity tracking
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
import random
import string
import secrets
from datetime import timedelta

# ============================================================================
# CONSTANTS
# ============================================================================

USER_ID_PREFIX = "USR"
USER_ID_LENGTH = 8
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# ============================================================================
# CUSTOM USER MANAGER
# ============================================================================

class CustomUserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError(_('Email address is required'))
        
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


# ============================================================================
# USER MODEL
# ============================================================================

class User(AbstractUser):
    """Custom User Model with email as primary identifier"""
    
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Admin')
        MANAGER = 'manager', _('Manager')
        OPERATOR = 'operator', _('Operator')
        VIEWER = 'viewer', _('Viewer')
    
    # Username is optional (we use email as primary)
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=False,
        blank=True,
        null=True,
        help_text=_('Optional. Used for display purposes only.')
    )
    
    # Email is the unique identifier
    email = models.EmailField(
        _('email address'),
        unique=True,
        db_index=True,
        error_messages={
            'unique': _('A user with this email already exists.'),
        }
    )
    
    # User profile fields
    user_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_("User ID"),
        help_text=_('Auto-generated unique identifier')
    )
    
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Phone Number"),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message=_('Phone number must be entered in format: +999999999')
            )
        ]
    )
    
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Department")
    )
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
        db_index=True,
        verbose_name=_("User Role")
    )
    
    # Security fields
    two_factor_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Two Factor Authentication")
    )
    
    email_verified = models.BooleanField(
        default=False,
        verbose_name=_("Email Verified")
    )
    
    phone_verified = models.BooleanField(
        default=False,
        verbose_name=_("Phone Verified")
    )
    
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Last Login IP")
    )
    
    last_activity = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Last Activity")
    )
    
    # Account lockout
    is_locked = models.BooleanField(
        default=False,
        verbose_name=_("Account Locked")
    )
    
    lockout_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Lockout Until")
    )
    
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name=_("Failed Login Attempts")
    )
    
    # Security tokens
    email_verification_token = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    password_reset_token = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    password_reset_expires = models.DateTimeField(
        null=True,
        blank=True
    )
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    
    # Use email as the unique identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email and password are required by default
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_id']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_locked']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.user_id})"
    
    def save(self, *args, **kwargs):
        """Auto-generate user_id and set defaults"""
        if not self.user_id:
            self.user_id = self._generate_user_id()
        
        # Set username from email if not provided
        if not self.username and self.email:
            self.username = self.email.split('@')[0]
        
        super().save(*args, **kwargs)
    
    def _generate_user_id(self):
        """Generate a unique user ID"""
        max_attempts = 100
        for _ in range(max_attempts):
            random_part = ''.join(random.choices(
                string.ascii_uppercase + string.digits, 
                k=USER_ID_LENGTH
            ))
            user_id = f"{USER_ID_PREFIX}{random_part}"
            if not User.objects.filter(user_id=user_id).exists():
                return user_id
        
        # Fallback: timestamp-based ID
        timestamp = str(int(timezone.now().timestamp()))[-8:]
        return f"{USER_ID_PREFIX}{timestamp}"
    
    @property
    def full_name(self):
        """Return full name or email"""
        name = self.get_full_name().strip()
        return name if name else self.email
    
    @property
    def is_locked_out(self):
        """Check if account is currently locked out"""
        if not self.is_locked:
            return False
        if self.lockout_until and self.lockout_until > timezone.now():
            return True
        # Auto-unlock if lockout period has passed
        self.is_locked = False
        self.failed_login_attempts = 0
        self.lockout_until = None
        self.save(update_fields=['is_locked', 'failed_login_attempts', 'lockout_until'])
        return False
    
    # ===== LOGIN METHODS =====
    
    def record_login(self, request):
        """Record successful login"""
        self.last_login = timezone.now()
        self.last_login_ip = self._get_client_ip(request)
        self.failed_login_attempts = 0
        self.is_locked = False
        self.lockout_until = None
        self.last_activity = timezone.now()
        self.save(update_fields=[
            'last_login', 'last_login_ip', 'failed_login_attempts',
            'is_locked', 'lockout_until', 'last_activity'
        ])
    
    def record_failed_login(self):
        """Record failed login attempt"""
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            self.is_locked = True
            self.lockout_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
        
        self.save(update_fields=['failed_login_attempts', 'is_locked', 'lockout_until'])
    
    def can_login(self):
        """Check if user can attempt login"""
        if not self.is_active:
            return False, _("Account is inactive")
        
        if self.is_locked_out:
            return False, _("Account is temporarily locked")
        
        return True, _("OK")
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


# ============================================================================
# LOGIN HISTORY MODEL
# ============================================================================

class LoginHistory(models.Model):
    """Track user login history"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history'
    )
    login_time = models.DateTimeField(auto_now_add=True, db_index=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    login_successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = _('Login History')
        verbose_name_plural = _('Login Histories')
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', 'login_time']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"


# ============================================================================
# USER ACTIVITY MODEL
# ============================================================================

class UserActivity(models.Model):
    """Track user activity in the system"""
    
    class ActivityType(models.TextChoices):
        LOGIN = 'login', _('Login')
        LOGOUT = 'logout', _('Logout')
        CREATE = 'create', _('Create')
        UPDATE = 'update', _('Update')
        DELETE = 'delete', _('Delete')
        VIEW = 'view', _('View')
        PRINT = 'print', _('Print')
        EXPORT = 'export', _('Export')
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        db_index=True
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField()
    description = models.CharField(max_length=255)
    
    # Optional: Track affected objects
    content_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    
    # Additional data
    data = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('User Activity')
        verbose_name_plural = _('User Activities')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['activity_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_activity_type_display()}"


# ============================================================================
# USER SESSION MODEL
# ============================================================================

class UserSession(models.Model):
    """Track active user sessions"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True, db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"