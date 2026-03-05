from django.contrib import admin
from .models import Vehicle, VehicleType, VehicleCategory, Owner

@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['code', 'created_at', 'updated_at']


@admin.register(VehicleCategory)
class VehicleCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created_at']
    search_fields = ['code', 'name']
    readonly_fields = ['code', 'created_at', 'updated_at']


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ['owner_id', 'name', 'created_at']
    search_fields = ['owner_id', 'name']
    readonly_fields = ['owner_id', 'created_at', 'updated_at']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['vin', 'vehicle_reg', 'vehicle_type', 'category', 'owner', 'expiry_date_formatted']
    list_filter = ['vehicle_type', 'category', 'expiry_date']
    search_fields = ['vin', 'vehicle_reg', 'owner__name']
    readonly_fields = ['vin', 'created_at', 'updated_at']
    autocomplete_fields = ['vehicle_type', 'category', 'owner']
    
    def expiry_date_formatted(self, obj):
        return obj.expiry_date_formatted
    expiry_date_formatted.short_description = 'Expiry'