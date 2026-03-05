"""
Vehicle management models for We Yone Pot - Digital Osusu Platform
Handles vehicle registration, types, categories, and owner management
"""

import re
import random
import string
from datetime import timedelta
from typing import Optional, Tuple

from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from dateutil.relativedelta import relativedelta

# ============================================================================
# CONSTANTS
# ============================================================================

VIN_LENGTH = 5
OWNER_ID_PREFIX = "OWN"
OWNER_ID_FORMAT = f"{OWNER_ID_PREFIX}{{:06d}}"
VIN_CHARS = string.ascii_uppercase.replace('I', '').replace('O', '').replace('Q', '') + string.digits

# ============================================================================
# VEHICLE TYPE MODEL
# ============================================================================

class VehicleType(models.Model):
    """
    Model for vehicle types (Commercial, Private, NGO, Diplomatic, etc.)
    """
    
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text=_("e.g., COM, PRV, NGO, DIP"),
        blank=True,
        verbose_name=_("Code")
    )
    
    name = models.CharField(
        max_length=50,
        help_text=_("e.g., Commercial, Private, NGO, Diplomatic"),
        verbose_name=_("Name")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Additional description of the vehicle type"),
        verbose_name=_("Description")
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether this vehicle type is currently active")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = _("Vehicle Type")
        verbose_name_plural = _("Vehicle Types")
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self) -> str:
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate code if not provided"""
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)
    
    def _generate_code(self) -> str:
        """Generate a unique code from name"""
        if self.name:
            # Take first 3 letters of name, uppercase and clean
            base_code = re.sub(r'[^A-Z]', '', self.name[:3].upper())
            if not base_code:  # If no letters, use default
                base_code = "TYP"
        else:
            base_code = "TYP"
        
        # Make it unique
        code = base_code
        counter = 1
        while VehicleType.objects.filter(code=code).exists():
            code = f"{base_code}{counter}"
            counter += 1
        return code
    
    @classmethod
    def get_active_types(cls):
        """Get all active vehicle types"""
        return cls.objects.filter(is_active=True)


# ============================================================================
# VEHICLE CATEGORY MODEL
# ============================================================================

class VehicleCategory(models.Model):
    """
    Model for vehicle categories (AP1, B1, B2, C1, etc.)
    """
    
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text=_("e.g., AP1, B1, B2, C1"),
        blank=True,
        verbose_name=_("Code")
    )
    
    name = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("e.g., Category AP1, Category B1"),
        verbose_name=_("Name")
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = _("Vehicle Category")
        verbose_name_plural = _("Vehicle Categories")
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self) -> str:
        return self.code
    
    def save(self, *args, **kwargs):
        """Auto-generate code if not provided"""
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)
    
    def _generate_code(self) -> str:
        """Generate a unique code"""
        if self.name:
            # Try to extract code from name if it looks like AP1, B1, etc.
            match = re.search(r'([A-Z0-9]{2,4})', self.name.upper())
            if match:
                base_code = match.group(1)
            else:
                base_code = re.sub(r'[^A-Z]', '', self.name[:3].upper())
                if not base_code:
                    base_code = "CAT"
        else:
            base_code = "CAT"
        
        # Make it unique
        code = base_code
        counter = 1
        while VehicleCategory.objects.filter(code=code).exists():
            code = f"{base_code}{counter}"
            counter += 1
        return code
    
    @classmethod
    def get_active_categories(cls):
        """Get all active vehicle categories"""
        return cls.objects.filter(is_active=True)


# ============================================================================
# OWNER MODEL
# ============================================================================

class Owner(models.Model):
    """
    Model for vehicle owners
    """
    
    owner_id = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_("Owner ID"),
        blank=True,
        help_text=_("Auto-generated owner ID")
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name=_("Owner Name"),
        db_index=True
    )
    
    contact_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_("Contact Number"),
        help_text=_("Phone number of the owner")
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name=_("Email Address")
    )
    
    address = models.TextField(
        blank=True,
        verbose_name=_("Address")
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Created By")
    )
    
    class Meta:
        ordering = ['name']
        verbose_name = _("Owner")
        verbose_name_plural = _("Owners")
        indexes = [
            models.Index(fields=['owner_id']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self) -> str:
        return f"{self.owner_id} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate owner_id if not provided"""
        if not self.owner_id:
            self.owner_id = self._generate_owner_id()
        super().save(*args, **kwargs)
    
    def _generate_owner_id(self) -> str:
        """Generate a unique owner ID"""
        last_owner = Owner.objects.filter(
            owner_id__startswith=OWNER_ID_PREFIX
        ).order_by('owner_id').last()
        
        if last_owner:
            last_number = int(last_owner.owner_id[len(OWNER_ID_PREFIX):])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return OWNER_ID_FORMAT.format(new_number)
    
    @property
    def vehicle_count(self) -> int:
        """Get number of vehicles owned"""
        return self.vehicles.count()
    
    @classmethod
    def get_active_owners(cls):
        """Get all active owners"""
        return cls.objects.filter(is_active=True)


# ============================================================================
# VEHICLE MODEL
# ============================================================================

class Vehicle(models.Model):
    """
    Main Vehicle model for registration and tracking
    """
    
    # VIN (Vehicle Identification Number)
    vin = models.CharField(
        max_length=VIN_LENGTH,
        unique=True,
        validators=[
            MinLengthValidator(VIN_LENGTH),
            MaxLengthValidator(VIN_LENGTH),
            RegexValidator(
                regex=r'^[A-HJ-NPR-Z0-9]{5}$',
                message=_('VIN must be 5 characters: letters (excluding I,O,Q) and numbers'),
                code='invalid_vin'
            )
        ],
        verbose_name=_("VIN"),
        help_text=_("5-character code (auto-generated)"),
        blank=True,
        db_index=True
    )

    # Vehicle registration number (e.g., "ABC 200")
    vehicle_reg = models.CharField(
        max_length=20,
        verbose_name=_("Vehicle Registration"),
        help_text=_("e.g., ABC 200"),
        blank=True,
        db_index=True
    )
    
    # Vehicle details - Foreign Keys
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.PROTECT,  # PROTECT prevents deletion if vehicles exist
        related_name='vehicles',
        verbose_name=_("Vehicle Type"),
        limit_choices_to={'is_active': True}
    )
    
    category = models.ForeignKey(
        VehicleCategory,
        on_delete=models.SET_NULL,  # SET_NULL allows category to be deleted
        null=True,
        blank=True,
        related_name='vehicles',
        verbose_name=_("Vehicle Category"),
        help_text=_("e.g., AP1, B1, B2"),
        limit_choices_to={'is_active': True}
    )
    
    # Owner information - Foreign Key to Owner model
    owner = models.ForeignKey(
        Owner,
        on_delete=models.PROTECT,  # PROTECT prevents deletion if vehicles exist
        related_name='vehicles',
        verbose_name=_("Owner"),
        limit_choices_to={'is_active': True}
    )
    
    # Additional vehicle information
    make = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Make"),
        help_text=_("e.g., Toyota, Nissan, Honda")
    )
    
    model = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Model"),
        help_text=_("e.g., Corolla, Hilux, Camry")
    )
    
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Year"),
        help_text=_("Manufacturing year")
    )
    
    color = models.CharField(
        max_length=30,
        blank=True,
        verbose_name=_("Color")
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether this vehicle registration is active")
    )
    
    # Expiry date - automatically set on creation
    expiry_date = models.DateField(
        verbose_name=_("Expiry Date"),
        help_text=_("Format: MM/YYYY"),
        blank=True,
        null=True,
        db_index=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Created By")
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Vehicle")
        verbose_name_plural = _("Vehicles")
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['vehicle_reg']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['vehicle_type']),
            models.Index(fields=['category']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
        permissions = [
            ('can_print_vehicle_card', 'Can print vehicle card'),
            ('can_renew_vehicle', 'Can renew vehicle registration'),
        ]
    
    def __str__(self) -> str:
        vehicle_type_code = self.vehicle_type.code if self.vehicle_type else "No Type"
        owner_name = self.owner.name if self.owner else "No Owner"
        reg_display = f" [{self.vehicle_reg}]" if self.vehicle_reg else ""
        return f"{vehicle_type_code} - {self.vin}{reg_display} - {owner_name}"
    
    def clean(self):
        """Model validation"""
        super().clean()
        
        # Validate expiry_date format
        if self.expiry_date:
            # Ensure expiry_date is first day of month
            if self.expiry_date.day != 1:
                self.expiry_date = self.expiry_date.replace(day=1)
    
    def save(self, *args, **kwargs):
        """Override save to add auto-generation and validation"""
        # Auto-generate VIN if not provided
        if not self.vin:
            self.vin = self._generate_vin()
        
        # Only set expiry_date on creation if not already set
        if not self.pk and not self.expiry_date:
            self._set_initial_expiry_date()
        
        # Clean before save
        self.clean()
        
        super().save(*args, **kwargs)
    
    def _generate_vin(self) -> str:
        """
        Generate a random 5-character VIN
        Excludes I, O, Q to avoid confusion with 1 and 0
        """
        max_attempts = 100
        for _ in range(max_attempts):
            vin = ''.join(random.choices(VIN_CHARS, k=VIN_LENGTH))
            if not Vehicle.objects.filter(vin=vin).exists():
                return vin
        
        # Fallback: timestamp-based
        timestamp = str(int(timezone.now().timestamp()))[-5:]
        return f"V{timestamp}"
    
    def _set_initial_expiry_date(self):
        """Set initial expiry date to first day of next month, one year ahead"""
        current_date = timezone.now().date()
        next_year = current_date + relativedelta(years=1)
        self.expiry_date = next_year.replace(day=1)
    
    def renew(self, years: int = 1) -> 'Vehicle':
        """
        Renew vehicle registration by extending expiry date
        
        Args:
            years: Number of years to extend
            
        Returns:
            Vehicle: Updated vehicle instance
        """
        if not self.expiry_date:
            self._set_initial_expiry_date()
        else:
            # Add years to current expiry
            new_date = self.expiry_date + relativedelta(years=years)
            self.expiry_date = new_date.replace(day=1)
        
        self.save()
        return self
    
    def is_expired(self) -> bool:
        """Check if vehicle registration is expired"""
        if not self.expiry_date:
            return False
        return timezone.now().date() > self.expiry_date
    
    def days_until_expiry(self) -> Optional[int]:
        """Get days until expiry (negative if expired)"""
        if not self.expiry_date:
            return None
        delta = self.expiry_date - timezone.now().date()
        return delta.days
    
    @property
    def expiry_date_formatted(self) -> str:
        """Return expiry_date formatted as MM/YYYY"""
        if self.expiry_date:
            return self.expiry_date.strftime("%m/%Y")
        return ""
    
    @property
    def card_number(self) -> str:
        """Generate a card number for printing"""
        return f"VH{self.pk:06d}{self.vin}"
    
    @property
    def vehicle_type_code(self) -> str:
        """Return vehicle type code"""
        return self.vehicle_type.code if self.vehicle_type else ""
    
    @property
    def vehicle_type_name(self) -> str:
        """Return vehicle type name"""
        return self.vehicle_type.name if self.vehicle_type else ""
    
    @property
    def category_code(self) -> str:
        """Return category code"""
        return self.category.code if self.category else ""
    
    @property
    def owner_id(self) -> str:
        """Return owner ID"""
        return self.owner.owner_id if self.owner else ""
    
    @property
    def owner_name(self) -> str:
        """Return owner name"""
        return self.owner.name if self.owner else ""
    
    @classmethod
    def get_expiring_soon(cls, days: int = 30):
        """
        Get vehicles expiring within specified days
        
        Args:
            days: Number of days threshold
            
        Returns:
            QuerySet: Vehicles expiring soon
        """
        today = timezone.now().date()
        threshold = today + timedelta(days=days)
        return cls.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=threshold,
            is_active=True
        ).select_related('owner', 'vehicle_type')
    
    @classmethod
    def get_expired(cls):
        """Get expired vehicles"""
        today = timezone.now().date()
        return cls.objects.filter(
            expiry_date__lt=today,
            is_active=True
        ).select_related('owner', 'vehicle_type')


# ============================================================================
# PRINT LOG MODEL
# ============================================================================
class PrintLog(models.Model):
    """
    Model to track document print events for vehicles.
    """
    vehicle = models.ForeignKey(
        'Vehicle', 
        on_delete=models.CASCADE, 
        related_name='print_logs'
    )
    printed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    printed_by = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-printed_at']
        indexes = [
            models.Index(fields=['printed_at']),
            models.Index(fields=['vehicle', 'printed_at']),
        ]
        verbose_name = 'Print Log'
        verbose_name_plural = 'Print Logs'
    
    def __str__(self):
        return f"Print {self.vehicle} at {self.printed_at}"