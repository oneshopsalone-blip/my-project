"""
Account management forms for We Yone Pot - Digital Osusu Platform
Handles user registration, authentication, and profile updates
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import User
import re

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

PASSWORD_MIN_LENGTH = 12
PASSWORD_REGEX = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).+$')


# ============================================================================
# CUSTOM USER CREATION FORM
# ============================================================================

class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users (admin only)"""
    
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Email address'),
            'autofocus': True
        })
    )
    
    first_name = forms.CharField(
        label=_('First Name'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('First name')
        })
    )
    
    last_name = forms.CharField(
        label=_('Last Name'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Last name')
        })
    )
    
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Password')
        }),
        help_text=_(
            f'Password must be at least {PASSWORD_MIN_LENGTH} characters long, '
            'contain at least one uppercase letter, one lowercase letter, '
            'one number, and one special character.'
        )
    )
    
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm password')
        })
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('A user with this email already exists.'))
        return email
    
    def clean_password1(self):
        """Validate password strength"""
        password = self.cleaned_data.get('password1')
        
        if len(password) < PASSWORD_MIN_LENGTH:
            raise forms.ValidationError(
                _(f'Password must be at least {PASSWORD_MIN_LENGTH} characters long.')
            )
        
        if not PASSWORD_REGEX.match(password):
            raise forms.ValidationError(_(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one number, and one special character.'
            ))
        
        return password
    
    def save(self, commit=True):
        """Save user with username set to email"""
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user


# ============================================================================
# CUSTOM USER CHANGE FORM
# ============================================================================

class CustomUserChangeForm(UserChangeForm):
    """Form for updating users"""
    
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': True  # Email cannot be changed
        })
    )
    
    first_name = forms.CharField(
        label=_('First Name'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        label=_('Last Name'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    phone_number = forms.CharField(
        label=_('Phone Number'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    department = forms.CharField(
        label=_('Department'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 
                  'department', 'is_active', 'is_superuser', 'role')


# ============================================================================
# CUSTOM AUTHENTICATION FORM
# ============================================================================

class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form with remember me functionality"""
    
    username = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email'),
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password')
        })
    )
    
    remember_me = forms.BooleanField(
        label=_('Remember me'),
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    error_messages = {
        'invalid_login': _('Invalid email or password.'),
        'inactive': _('This account is inactive.'),
        'locked': _('Account is temporarily locked. Please try again later.'),
    }
    
    def confirm_login_allowed(self, user):
        """Override to check if user is superuser"""
        if not user.is_superuser:
            raise forms.ValidationError(
                _('Access denied. Admin privileges required.'),
                code='not_superuser'
            )
        super().confirm_login_allowed(user)


# ============================================================================
# PASSWORD CHANGE FORM
# ============================================================================

class PasswordChangeForm(forms.Form):
    """Form for changing password"""
    
    old_password = forms.CharField(
        label=_('Current Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    new_password1 = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_old_password(self):
        """Validate old password"""
        old_password = self.cleaned_data.get('old_password')
        if not self.user.check_password(old_password):
            raise forms.ValidationError(_('Current password is incorrect.'))
        return old_password
    
    def clean_new_password1(self):
        """Validate new password strength"""
        password = self.cleaned_data.get('new_password1')
        
        if len(password) < PASSWORD_MIN_LENGTH:
            raise forms.ValidationError(
                _(f'Password must be at least {PASSWORD_MIN_LENGTH} characters long.')
            )
        
        if not PASSWORD_REGEX.match(password):
            raise forms.ValidationError(_(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one number, and one special character.'
            ))
        
        return password
    
    def clean(self):
        """Validate passwords match"""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError(_('New passwords do not match.'))
        
        return cleaned_data
    
    def save(self):
        """Save new password"""
        self.user.set_password(self.cleaned_data['new_password1'])
        self.user.last_password_change = timezone.now()
        self.user.save()
        return self.user


# ============================================================================
# PROFILE UPDATE FORM
# ============================================================================

class ProfileUpdateForm(forms.ModelForm):
    """Form for users to update their profile"""
    
    first_name = forms.CharField(
        label=_('First Name'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        label=_('Last Name'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    phone_number = forms.CharField(
        label=_('Phone Number'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    department = forms.CharField(
        label=_('Department'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'department')
    
    def clean_phone_number(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Remove common separators
            cleaned = re.sub(r'[\s\-\(\)]', '', phone)
            if not cleaned.startswith('+') and not cleaned.isdigit():
                raise forms.ValidationError(
                    _('Phone number must contain only digits and optional + prefix.')
                )
        return phone