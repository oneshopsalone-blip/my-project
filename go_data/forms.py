"""
Forms for vehicle management in We Yone Pot - Digital Osusu Platform
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
import re

from .models import (
    Vehicle, VehicleType, VehicleCategory, Owner, PrintLog
)


class VehicleTypeForm(forms.ModelForm):
    """Form for creating and updating vehicle types"""
    
    class Meta:
        model = VehicleType
        fields = ['code', 'name', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., COM')
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Commercial')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_code(self):
        """Ensure code is uppercase"""
        code = self.cleaned_data.get('code')
        if code:
            return code.upper()
        return code


class VehicleCategoryForm(forms.ModelForm):
    """Form for creating and updating vehicle categories"""
    
    class Meta:
        model = VehicleCategory
        fields = ['vehicle_type', 'code', 'name', 'is_active']
        widgets = {
            'vehicle_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_vehicle_type'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., AP1'),
                'required': True  # Make it required
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., Category AP1')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active vehicle types
        self.fields['vehicle_type'].queryset = VehicleType.get_active_types()
        self.fields['code'].required = True  # Ensure code is required
    
    def clean_code(self):
        """Ensure code is uppercase and doesn't contain spaces"""
        code = self.cleaned_data.get('code')
        if code:
            # Remove spaces and convert to uppercase
            code = code.upper().replace(' ', '')
            
            # Optional: Validate format if needed
            if not re.match(r'^[A-Z0-9]+$', code):
                raise ValidationError(
                    _('Code can only contain letters and numbers.')
                )
        return code
    
    # Remove the clean method that checks uniqueness since we now do it in the model

    
class OwnerForm(forms.ModelForm):
    """Form for creating and updating vehicle owners"""
    
    class Meta:
        model = Owner
        fields = ['name', 'is_active', 'created_by']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter owner name')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'created_by': forms.HiddenInput(),  # Usually set automatically
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set created_by if user is provided
        if self.user and not self.instance.pk:
            self.fields['created_by'].initial = self.user.username


class VehicleForm(forms.ModelForm):
    """Main form for vehicle registration with dynamic category filtering"""
    
    class Meta:
        model = Vehicle
        fields = [
            'vin', 'vehicle_reg', 'vehicle_type', 'category', 
            'owner', 'is_active', 'expiry_date', 'created_by'
        ]
        widgets = {
            'vin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Auto-generated if blank'),
                'maxlength': '5',
                'style': 'text-transform:uppercase'
            }),
            'vehicle_reg': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., ABC 200')
            }),
            'vehicle_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_vehicle_type',  # Important for JavaScript
                'data-dependent': '#id_category'  # Custom attribute for JS
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category'
            }),
            'owner': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',  # HTML5 month input
                'placeholder': _('MM/YYYY')
            }),
            'created_by': forms.HiddenInput(),
        }
        labels = {
            'vin': _('VIN (Vehicle Identification Number)'),
            'vehicle_reg': _('Registration Number'),
            'vehicle_type': _('Vehicle Type'),
            'category': _('Category'),
            'owner': _('Owner'),
            'is_active': _('Active'),
            'expiry_date': _('Expiry Date'),
        }
        help_texts = {
            'vin': _('5-character code. Leave blank to auto-generate.'),
            'expiry_date': _('Format: MM/YYYY (will be set to first day of month)'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limit choices to active records
        self.fields['vehicle_type'].queryset = VehicleType.get_active_types()
        self.fields['owner'].queryset = Owner.get_active_owners()
        
        # Initially, show all active categories or filter based on existing instance
        if self.instance.pk and self.instance.vehicle_type:
            # If editing existing vehicle, show categories for its vehicle type
            self.fields['category'].queryset = VehicleCategory.get_active_categories(
                vehicle_type=self.instance.vehicle_type
            )
        else:
            # For new vehicles, show all active categories initially
            # (will be filtered dynamically via JavaScript)
            self.fields['category'].queryset = VehicleCategory.objects.filter(is_active=True)
        
        # Set created_by if user is provided and creating new instance
        if self.user and not self.instance.pk:
            self.fields['created_by'].initial = self.user.username
        
        # Make vin not required since it can be auto-generated
        self.fields['vin'].required = False
    
    def clean_vin(self):
        """Validate VIN format"""
        vin = self.cleaned_data.get('vin')
        if vin:
            # Ensure uppercase
            vin = vin.upper()
            # Basic format validation
            if not re.match(r'^[A-HJ-NPR-Z0-9]{5}$', vin):
                raise ValidationError(
                    _('VIN must be 5 characters: letters (excluding I,O,Q) and numbers')
                )
        return vin
    
    def clean_expiry_date(self):
        """Validate and format expiry date"""
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date:
            # Ensure it's the first day of the month
            if expiry_date.day != 1:
                expiry_date = expiry_date.replace(day=1)
        return expiry_date
    
    def clean(self):
        """Validate that category belongs to selected vehicle type"""
        cleaned_data = super().clean()
        vehicle_type = cleaned_data.get('vehicle_type')
        category = cleaned_data.get('category')
        
        if vehicle_type and category and category.vehicle_type != vehicle_type:
            self.add_error(
                'category', 
                _('Selected category does not belong to the selected vehicle type.')
            )
        
        return cleaned_data


class VehicleRenewForm(forms.Form):
    """Form for renewing vehicle registration"""
    
    years = forms.IntegerField(
        label=_('Renewal Period (Years)'),
        min_value=1,
        max_value=5,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5'
        })
    )
    confirm = forms.BooleanField(
        label=_('Confirm Renewal'),
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean_years(self):
        years = self.cleaned_data.get('years')
        if years and years not in range(1, 6):
            raise ValidationError(_('Renewal period must be between 1 and 5 years'))
        return years


class VehicleSearchForm(forms.Form):
    """Form for searching/filtering vehicles"""
    
    q = forms.CharField(
        label=_('Search'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by VIN, registration, or owner...')
        })
    )
    
    vehicle_type = forms.ModelChoiceField(
        label=_('Vehicle Type'),
        queryset=VehicleType.objects.all(),
        required=False,
        empty_label=_('All Types'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'search_vehicle_type'
        })
    )
    
    category = forms.ModelChoiceField(
        label=_('Category'),
        queryset=VehicleCategory.objects.all(),
        required=False,
        empty_label=_('All Categories'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'search_category'
        })
    )
    
    owner = forms.ModelChoiceField(
        label=_('Owner'),
        queryset=Owner.objects.all(),
        required=False,
        empty_label=_('All Owners'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        label=_('Status'),
        required=False,
        choices=[
            ('', _('All')),
            ('active', _('Active')),
            ('expired', _('Expired')),
            ('expiring_soon', _('Expiring Soon')),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit to active records for dropdowns
        self.fields['vehicle_type'].queryset = VehicleType.get_active_types()
        self.fields['owner'].queryset = Owner.get_active_owners()
        # Show all active categories initially
        self.fields['category'].queryset = VehicleCategory.objects.filter(is_active=True)


class VehicleBulkUploadForm(forms.Form):
    """Form for bulk uploading vehicles via CSV/Excel"""
    
    file = forms.FileField(
        label=_('Upload File'),
        help_text=_('Upload CSV or Excel file with vehicle data'),
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    
    created_by = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['created_by'].initial = self.user.username


class PrintLogForm(forms.ModelForm):
    """Form for creating print log entries"""
    
    class Meta:
        model = PrintLog
        fields = ['vehicle', 'printed_by', 'ip_address', 'user_agent']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'printed_by': forms.TextInput(attrs={'class': 'form-control'}),
            'ip_address': forms.HiddenInput(),
            'user_agent': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if request:
            # Auto-populate from request
            if not self.instance.pk:
                self.fields['printed_by'].initial = request.user.username
                self.fields['ip_address'].initial = self._get_client_ip(request)
                self.fields['user_agent'].initial = request.META.get('HTTP_USER_AGENT', '')
    
    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')