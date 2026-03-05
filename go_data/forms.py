
"""
Vehicle management forms for We Yone Pot - Digital Osusu Platform
Handles form validation and rendering for vehicle-related models
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import re

from .models import (
    Vehicle, VehicleType, VehicleCategory, Owner, 
    VIN_LENGTH, VIN_CHARS
)


# ============================================================================
# VEHICLE TYPE FORMS
# ============================================================================

class VehicleTypeForm(forms.ModelForm):
    """Form for creating and editing vehicle types"""
    
    class Meta:
        model = VehicleType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Commercial'),
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Enter description (optional)'),
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'name': _('Code will be auto-generated from the name (e.g., Commercial → COM)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make description optional
        self.fields['description'].required = False
        
        # If editing existing object, show the code
        if self.instance and self.instance.pk:
            self.fields['code_display'] = forms.CharField(
                label=_('Code'),
                initial=self.instance.code,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'disabled': True
                }),
                required=False
            )
            # Insert code_display at the beginning
            self.fields.insert(0, 'code_display', self.fields.pop('code_display'))

    def clean_name(self):
        """Validate and clean name"""
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError(_('Name is required.'))
        
        # Check for minimum length
        if len(name) < 2:
            raise ValidationError(_('Name must be at least 2 characters long.'))
        
        return name.strip()


# ============================================================================
# VEHICLE CATEGORY FORMS
# ============================================================================

class VehicleCategoryForm(forms.ModelForm):
    """Form for creating and editing vehicle categories"""
    
    class Meta:
        model = VehicleCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., AP1, B1, B2, C1'),
                'autofocus': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Enter description (optional)'),
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'name': _('Code will be auto-generated (e.g., "AP1" or first letters of name)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make name optional for categories
        self.fields['name'].required = False
        self.fields['description'].required = False
        
        # If editing existing object, show the code
        if self.instance and self.instance.pk:
            self.fields['code_display'] = forms.CharField(
                label=_('Code'),
                initial=self.instance.code,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'disabled': True
                }),
                required=False
            )
            # Insert code_display at the beginning
            self.fields.insert(0, 'code_display', self.fields.pop('code_display'))


# ============================================================================
# OWNER FORMS
# ============================================================================

class OwnerForm(forms.ModelForm):
    """Form for creating and editing vehicle owners"""
    
    class Meta:
        model = Owner
        fields = ['name', 'contact_number', 'email', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Owner full name'),
                'autofocus': True
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., +232 76 123 456')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('owner@example.com')
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Physical address'),
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'name': _('Owner ID will be auto-generated (e.g., OWN000001)'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make optional fields
        self.fields['contact_number'].required = False
        self.fields['email'].required = False
        self.fields['address'].required = False
        
        # If editing existing object, show the owner_id
        if self.instance and self.instance.pk:
            self.fields['owner_id_display'] = forms.CharField(
                label=_('Owner ID'),
                initial=self.instance.owner_id,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'disabled': True
                }),
                required=False
            )
            self.fields.insert(0, 'owner_id_display', self.fields.pop('owner_id_display'))
            
            # Show vehicle count
            self.fields['vehicle_count_display'] = forms.CharField(
                label=_('Vehicles Owned'),
                initial=self.instance.vehicle_count,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'disabled': True
                }),
                required=False
            )
            self.fields['vehicle_count_display'] = self.fields.pop('vehicle_count_display')

    def clean_email(self):
        """Validate email format"""
        email = self.cleaned_data.get('email')
        if email:
            # Basic email validation
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                raise ValidationError(_('Enter a valid email address.'))
        return email

    def clean_contact_number(self):
        """Validate contact number format"""
        number = self.cleaned_data.get('contact_number')
        if number:
            # Remove common separators
            cleaned = re.sub(r'[\s\-\(\)\+]', '', number)
            if not cleaned.isdigit():
                raise ValidationError(_('Contact number should contain only digits and basic separators.'))
        return number


# ============================================================================
# VEHICLE FORMS
# ============================================================================

class VehicleForm(forms.ModelForm):
    """Main form for creating and editing vehicles"""
    
    # Additional fields for display
    days_until_expiry = forms.IntegerField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': True,
            'disabled': True
        })
    )
    
    class Meta:
        model = Vehicle
        fields = [
            'vin', 'vehicle_reg', 'vehicle_type', 'category', 
            'make', 'model', 'year', 'color',
            'owner', 'expiry_date', 'is_active'
        ]
        widgets = {
            'vin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Leave blank to auto-generate'),
                'maxlength': str(VIN_LENGTH),
                'style': 'text-transform:uppercase',
                'pattern': '[A-HJ-NPR-Z0-9]{5}',
                'title': _('5 characters: A-Z (excluding I,O,Q) and 0-9')
            }),
            'vehicle_reg': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., ABC 200')
            }),
            'vehicle_type': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'make': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Toyota')
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Corolla')
            }),
            'year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('YYYY'),
                'min': 1900,
                'max': timezone.now().year + 1
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Red')
            }),
            'owner': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'expiry_date': forms.DateInput(
                attrs={
                    'type': 'month',
                    'class': 'form-control',
                    'pattern': '[0-9]{4}-[0-9]{2}'
                },
                format='%Y-%m'
            ),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'vin': _(f'Leave blank to auto-generate ({VIN_LENGTH} characters)'),
            'expiry_date': _('Select month and year (auto-sets to one year ahead if blank)'),
            'vehicle_type': _('Select vehicle type'),
            'category': _('Select category (optional)'),
            'owner': _('Select vehicle owner'),
            'year': _(f'Year between 1900 and {timezone.now().year + 1}'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make fields optional
        self.fields['vin'].required = False
        self.fields['expiry_date'].required = False
        self.fields['vehicle_reg'].required = False
        self.fields['category'].required = False
        self.fields['make'].required = False
        self.fields['model'].required = False
        self.fields['year'].required = False
        self.fields['color'].required = False
        
        # Add empty choices for optional foreign keys
        self.fields['category'].empty_label = _("Select Category (Optional)")
        
        # Filter active choices
        self.fields['vehicle_type'].queryset = VehicleType.objects.filter(is_active=True)
        self.fields['category'].queryset = VehicleCategory.objects.filter(is_active=True)
        self.fields['owner'].queryset = Owner.objects.filter(is_active=True)
        
        # Format expiry date if exists
        if self.instance and self.instance.expiry_date:
            self.initial['expiry_date'] = self.instance.expiry_date.strftime('%Y-%m')
            
            # Calculate days until expiry
            days = self.instance.days_until_expiry()
            if days is not None:
                if days < 0:
                    self.initial['days_until_expiry'] = _('Expired')
                else:
                    self.initial['days_until_expiry'] = f'{days} days'
        
        # If editing existing object, show additional info
        if self.instance and self.instance.pk:
            # Show card number
            self.fields['card_number_display'] = forms.CharField(
                label=_('Card Number'),
                initial=self.instance.card_number,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'disabled': True
                }),
                required=False
            )
            self.fields.insert(0, 'card_number_display', self.fields.pop('card_number_display'))
            
            # Show created info
            self.fields['created_info'] = forms.CharField(
                label=_('Created'),
                initial=self.instance.created_at.strftime('%Y-%m-%d %H:%M'),
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'readonly': True,
                    'disabled': True
                }),
                required=False
            )
            self.fields['created_info'] = self.fields.pop('created_info')

    def clean_vin(self):
        """Validate VIN format"""
        vin = self.cleaned_data.get('vin', '')
        
        if vin:
            vin = vin.upper().strip()
            
            # Check length
            if len(vin) != VIN_LENGTH:
                raise ValidationError(
                    _(f'VIN must be exactly {VIN_LENGTH} characters long.')
                )
            
            # Check characters
            if not re.match(r'^[A-HJ-NPR-Z0-9]{5}$', vin):
                raise ValidationError(
                    _('VIN can only contain letters A-Z (excluding I, O, Q) and numbers.')
                )
            
            # Check uniqueness (except for current instance)
            queryset = Vehicle.objects.filter(vin=vin)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError(_('This VIN is already in use.'))
        
        return vin

    def clean_vehicle_reg(self):
        """Validate vehicle registration"""
        reg = self.cleaned_data.get('vehicle_reg', '')
        if reg:
            # Remove extra spaces
            reg = re.sub(r'\s+', ' ', reg.strip())
        return reg

    def clean_year(self):
        """Validate year"""
        year = self.cleaned_data.get('year')
        if year:
            current_year = timezone.now().year
            if year < 1900 or year > current_year + 1:
                raise ValidationError(
                    _(f'Year must be between 1900 and {current_year + 1}.')
                )
        return year

    def clean_expiry_date(self):
        """Validate expiry date"""
        date = self.cleaned_data.get('expiry_date')
        if date:
            # Ensure it's first day of month
            if date.day != 1:
                date = date.replace(day=1)
        return date


# ============================================================================
# VEHICLE SEARCH FORM
# ============================================================================

class VehicleSearchForm(forms.Form):
    """Form for searching/filtering vehicles"""
    
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by VIN, registration, owner...')
        })
    )
    
    vehicle_type = forms.ModelChoiceField(
        queryset=VehicleType.objects.filter(is_active=True),
        required=False,
        empty_label=_("All Types"),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    category = forms.ModelChoiceField(
        queryset=VehicleCategory.objects.filter(is_active=True),
        required=False,
        empty_label=_("All Categories"),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    owner = forms.ModelChoiceField(
        queryset=Owner.objects.filter(is_active=True),
        required=False,
        empty_label=_("All Owners"),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', _('All Status')),
            ('active', _('Active')),
            ('expired', _('Expired')),
            ('expiring_soon', _('Expiring Soon')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError(_('"From" date cannot be after "To" date.'))
        
        return cleaned_data


# ============================================================================
# BULK OPERATIONS FORMS
# ============================================================================

class VehicleBulkRenewForm(forms.Form):
    """Form for bulk renewing vehicles"""
    
    years = forms.IntegerField(
        label=_('Years to extend'),
        min_value=1,
        max_value=5,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 5
        })
    )
    
    confirm = forms.BooleanField(
        label=_('I confirm this bulk renewal operation'),
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class VehicleExportForm(forms.Form):
    """Form for exporting vehicle data"""
    
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
        ('pdf', 'PDF'),
    ]
    
    format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        initial='csv',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_expired = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )