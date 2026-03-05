"""
Vehicle management views for We Yone Pot - Digital Osusu Platform
Handles all vehicle-related views including CRUD operations, dashboard, and printing
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse, JsonResponse
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q, Max
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import logging

from .models import Vehicle, VehicleType, VehicleCategory, Owner, PrintLog
from .forms import (
    VehicleForm, VehicleTypeForm, VehicleCategoryForm, OwnerForm,
    VehicleSearchForm
)
from .services.pdf_generator import VehicleCardPDFGenerator

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client_ip(request):
    """Get client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_date_filter_params(request):
    """
    Extract and validate date filter parameters from request
    Returns tuple of (date_from_obj, date_to_obj)
    """
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    date_from_obj = None
    date_to_obj = None
    
    if date_from and date_to:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Invalid date format: from={date_from}, to={date_to}")
    
    return date_from_obj, date_to_obj


# ============================================================================
# DASHBOARD VIEW
# ============================================================================

class VehicleDashboardView(LoginRequiredMixin, ListView):
    """
    Dashboard view listing all vehicles with print statistics
    Requires authentication
    """
    model = Vehicle
    template_name = 'go_data/dashboard.html'
    context_object_name = 'vehicles'
    paginate_by = 20
    login_url = 'accounts:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
    
    def get_queryset(self):
        """Apply search and filter to queryset"""
        queryset = Vehicle.objects.select_related(
            'vehicle_type', 'category', 'owner'
        ).all()
        
        # Search filter
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(vehicle_reg__icontains=search) |
                Q(vin__icontains=search) |
                Q(owner__name__icontains=search) |
                Q(vehicle_type__code__icontains=search)
            )
        
        # Owner filter
        owner_id = self.request.GET.get('owner')
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        
        # Get date filters
        date_from_obj, date_to_obj = get_date_filter_params(self.request)
        
        if date_from_obj and date_to_obj:
            context['date_from'] = date_from_obj
            context['date_to'] = date_to_obj
        
        # Get all owners with print counts
        owners = Owner.objects.all()
        owners_with_counts = []
        total_prints = 0
        
        for owner in owners:
            print_logs = PrintLog.objects.filter(vehicle__owner=owner)
            
            if date_from_obj and date_to_obj:
                print_logs = print_logs.filter(
                    printed_at__date__gte=date_from_obj,
                    printed_at__date__lte=date_to_obj
                )
            
            count = print_logs.count()
            total_prints += count
            
            owners_with_counts.append({
                'id': owner.id,
                'name': owner.name,
                'owner_id': owner.owner_id,
                'print_count': count
            })
        
        # Sort by print count (highest first)
        owners_with_counts.sort(key=lambda x: x['print_count'], reverse=True)
        
        context.update({
            'total_types': VehicleType.objects.count(),
            'total_categories': VehicleCategory.objects.count(),
            'total_owners': Owner.objects.count(),
            'owners_with_counts': owners_with_counts,
            'total_prints': total_prints,
            'selected_owner_id': self.request.GET.get('owner'),
            'search_query': self.request.GET.get('search', ''),
            'total_vehicles': Vehicle.objects.count(),
            'now': timezone.now().date(),
            'search_form': VehicleSearchForm(self.request.GET),
        })
        
        return context


# ============================================================================
# PRINT TRACKING
# ============================================================================

@login_required(login_url='accounts:login')
def track_print(request, pk):
    """
    Track when a vehicle document is printed.
    Accepts POST requests only.
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed. Use POST.'
        }, status=405)
    
    try:
        vehicle = get_object_or_404(Vehicle, pk=pk)
        
        print_log = PrintLog.objects.create(
            vehicle=vehicle,
            printed_by=request.user.get_full_name() or request.user.username,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        logger.info(f"Print tracked: Vehicle {pk} by {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'print_id': print_log.id,
            'timestamp': print_log.printed_at.isoformat()
        })
        
    except Vehicle.DoesNotExist:
        logger.error(f"Print tracking failed: Vehicle {pk} not found")
        return JsonResponse({
            'success': False,
            'error': 'Vehicle not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error tracking print for vehicle {pk}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required(login_url='accounts:login')
def get_print_stats(request):
    """API endpoint to get print statistics"""
    vehicle_id = request.GET.get('vehicle_id')
    owner_id = request.GET.get('owner_id')
    date_from_obj, date_to_obj = get_date_filter_params(request)
    
    queryset = PrintLog.objects.all()
    
    if vehicle_id:
        queryset = queryset.filter(vehicle_id=vehicle_id)
    
    if owner_id:
        queryset = queryset.filter(vehicle__owner_id=owner_id)
    
    if date_from_obj and date_to_obj:
        queryset = queryset.filter(
            printed_at__date__gte=date_from_obj,
            printed_at__date__lte=date_to_obj
        )
    
    # Get popular vehicles
    days = int(request.GET.get('days', 30))
    popular_vehicles = get_popular_vehicles(limit=5, days=days)
    
    # Group by date
    stats_by_date = queryset.extra(
        {'print_date': "date(printed_at)"}
    ).values('print_date').annotate(
        count=Count('id')
    ).order_by('-print_date')
    
    return JsonResponse({
        'success': True,
        'total': queryset.count(),
        'by_date': list(stats_by_date),
        'popular_vehicles': [
            {
                'id': v.id,
                'vin': v.vin,
                'vehicle_reg': v.vehicle_reg,
                'print_count': getattr(v, 'print_count', 0)
            } for v in popular_vehicles
        ]
    })


def get_popular_vehicles(limit=10, days=30):
    """Get most printed vehicles in the last N days."""
    since = timezone.now() - timedelta(days=days)
    return Vehicle.objects.filter(
        print_logs__printed_at__gte=since
    ).annotate(
        print_count=Count('print_logs')
    ).order_by('-print_count')[:limit]


def get_owner_print_summary(owner_id, days=30):
    """Get print summary for a specific owner."""
    since = timezone.now() - timedelta(days=days)
    return PrintLog.objects.filter(
        vehicle__owner_id=owner_id,
        printed_at__gte=since
    ).aggregate(
        total_prints=Count('id'),
        vehicles_printed=Count('vehicle', distinct=True),
        last_print=Max('printed_at')
    )


# ============================================================================
# VEHICLE CRUD
# ============================================================================

@login_required(login_url='accounts:login')
def vehicle_create(request):
    """Create a new vehicle"""
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save()
            messages.success(
                request, 
                f'Vehicle {vehicle.vehicle_reg or vehicle.vin} created successfully!'
            )
            return redirect('vehicles:dashboard')
    else:
        form = VehicleForm()
    
    return render(request, 'go_data/vehicle_form.html', {
        'form': form,
        'title': 'Add New Vehicle'
    })


@login_required(login_url='accounts:login')
def vehicle_update(request, pk):
    """Update an existing vehicle"""
    vehicle = get_object_or_404(Vehicle, pk=pk)
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                f'Vehicle {vehicle.vehicle_reg or vehicle.vin} updated successfully!'
            )
            return redirect('vehicles:dashboard')
    else:
        form = VehicleForm(instance=vehicle)
    
    return render(request, 'go_data/vehicle_form.html', {
        'form': form,
        'vehicle': vehicle,
        'title': f'Edit Vehicle: {vehicle.vehicle_reg or vehicle.vin}'
    })


@login_required(login_url='accounts:login')
def vehicle_delete(request, pk):
    """Delete a vehicle"""
    vehicle = get_object_or_404(Vehicle, pk=pk)
    
    if request.method == 'POST':
        vehicle_name = vehicle.vehicle_reg or vehicle.vin
        vehicle.delete()
        messages.success(request, f'Vehicle {vehicle_name} deleted successfully!')
        return redirect('vehicles:dashboard')
    
    return render(request, 'go_data/vehicle_confirm_delete.html', {
        'vehicle': vehicle
    })


@login_required(login_url='accounts:login')
def vehicle_detail(request, pk):
    """View vehicle details"""
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('vehicle_type', 'category', 'owner'), 
        pk=pk
    )
    return render(request, 'go_data/vehicle_detail.html', {
        'vehicle': vehicle,
        'now': timezone.now().date(),
    })


# ============================================================================
# VEHICLE TYPE CRUD
# ============================================================================

@login_required(login_url='accounts:login')
def vehicle_type_list(request):
    """List all vehicle types"""
    types = VehicleType.objects.all()
    return render(request, 'go_data/vehicle_type_list.html', {'types': types})


@login_required(login_url='accounts:login')
def vehicle_type_create(request):
    """Create a new vehicle type"""
    if request.method == 'POST':
        form = VehicleTypeForm(request.POST)
        if form.is_valid():
            vehicle_type = form.save()
            messages.success(
                request, 
                f'Vehicle type {vehicle_type.code} created successfully!'
            )
            return redirect('vehicles:vehicle_type_list')
    else:
        form = VehicleTypeForm()
    
    return render(request, 'go_data/vehicle_type_form.html', {
        'form': form,
        'title': 'Add Vehicle Type'
    })


@login_required(login_url='accounts:login')
def vehicle_type_update(request, pk):
    """Update a vehicle type"""
    vehicle_type = get_object_or_404(VehicleType, pk=pk)
    
    if request.method == 'POST':
        form = VehicleTypeForm(request.POST, instance=vehicle_type)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                f'Vehicle type {vehicle_type.code} updated successfully!'
            )
            return redirect('vehicles:vehicle_type_list')
    else:
        form = VehicleTypeForm(instance=vehicle_type)
    
    return render(request, 'go_data/vehicle_type_form.html', {
        'form': form,
        'object': vehicle_type,
        'title': f'Edit Vehicle Type: {vehicle_type.code}'
    })


@login_required(login_url='accounts:login')
def vehicle_type_delete(request, pk):
    """Delete a vehicle type"""
    vehicle_type = get_object_or_404(VehicleType, pk=pk)
    
    if request.method == 'POST':
        if vehicle_type.vehicles.exists():
            messages.error(
                request, 
                f'Cannot delete {vehicle_type.code} because it has vehicles assigned.'
            )
            return redirect('vehicles:vehicle_type_list')
        
        vehicle_type.delete()
        messages.success(
            request, 
            f'Vehicle type {vehicle_type.code} deleted successfully!'
        )
        return redirect('vehicles:vehicle_type_list')
    
    return render(request, 'go_data/vehicle_type_confirm_delete.html', {
        'object': vehicle_type
    })


# ============================================================================
# VEHICLE CATEGORY CRUD
# ============================================================================

@login_required(login_url='accounts:login')
def vehicle_category_list(request):
    """List all vehicle categories"""
    categories = VehicleCategory.objects.all()
    return render(request, 'go_data/vehicle_category_list.html', {'categories': categories})


@login_required(login_url='accounts:login')
def vehicle_category_create(request):
    """Create a new vehicle category"""
    if request.method == 'POST':
        form = VehicleCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(
                request, 
                f'Category {category.code} created successfully!'
            )
            return redirect('vehicles:vehicle_category_list')
    else:
        form = VehicleCategoryForm()
    
    return render(request, 'go_data/vehicle_category_form.html', {
        'form': form,
        'title': 'Add Vehicle Category'
    })


@login_required(login_url='accounts:login')
def vehicle_category_update(request, pk):
    """Update a vehicle category"""
    category = get_object_or_404(VehicleCategory, pk=pk)
    
    if request.method == 'POST':
        form = VehicleCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                f'Category {category.code} updated successfully!'
            )
            return redirect('vehicles:vehicle_category_list')
    else:
        form = VehicleCategoryForm(instance=category)
    
    return render(request, 'go_data/vehicle_category_form.html', {
        'form': form,
        'object': category,
        'title': f'Edit Category: {category.code}'
    })


@login_required(login_url='accounts:login')
def vehicle_category_delete(request, pk):
    """Delete a vehicle category"""
    category = get_object_or_404(VehicleCategory, pk=pk)
    
    if request.method == 'POST':
        if category.vehicles.exists():
            messages.error(
                request, 
                f'Cannot delete {category.code} because it has vehicles assigned.'
            )
            return redirect('vehicles:vehicle_category_list')
        
        category.delete()
        messages.success(
            request, 
            f'Category {category.code} deleted successfully!'
        )
        return redirect('vehicles:vehicle_category_list')
    
    return render(request, 'go_data/vehicle_category_confirm_delete.html', {
        'object': category
    })


# ============================================================================
# OWNER CRUD
# ============================================================================

@login_required(login_url='accounts:login')
def owner_list(request):
    """List all owners"""
    owners = Owner.objects.all()
    return render(request, 'go_data/owner_list.html', {'owners': owners})


@login_required(login_url='accounts:login')
def owner_create(request):
    """Create a new owner"""
    if request.method == 'POST':
        form = OwnerForm(request.POST)
        if form.is_valid():
            owner = form.save()
            messages.success(
                request, 
                f'Owner {owner.owner_id} - {owner.name} created successfully!'
            )
            return redirect('vehicles:owner_list')
    else:
        form = OwnerForm()
    
    return render(request, 'go_data/owner_form.html', {
        'form': form,
        'title': 'Add Owner'
    })


@login_required(login_url='accounts:login')
def owner_update(request, pk):
    """Update an owner"""
    owner = get_object_or_404(Owner, pk=pk)
    
    if request.method == 'POST':
        form = OwnerForm(request.POST, instance=owner)
        if form.is_valid():
            form.save()
            messages.success(request, f'Owner {owner.name} updated successfully!')
            return redirect('vehicles:owner_list')
    else:
        form = OwnerForm(instance=owner)
    
    return render(request, 'go_data/owner_form.html', {
        'form': form,
        'object': owner,
        'title': f'Edit Owner: {owner.name}'
    })


@login_required(login_url='accounts:login')
def owner_delete(request, pk):
    """Delete an owner"""
    owner = get_object_or_404(Owner, pk=pk)
    
    if request.method == 'POST':
        if owner.vehicles.exists():
            messages.error(
                request, 
                f'Cannot delete {owner.name} because they have vehicles assigned.'
            )
            return redirect('vehicles:owner_list')
        
        owner.delete()
        messages.success(request, f'Owner {owner.name} deleted successfully!')
        return redirect('vehicles:owner_list')
    
    return render(request, 'go_data/owner_confirm_delete.html', {
        'object': owner
    })


# ============================================================================
# PRINT FUNCTIONS
# ============================================================================

@login_required(login_url='accounts:login')
def print_vehicle_card(request, pk):
    """Generate and return vehicle card PDF"""
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('vehicle_type', 'category', 'owner'), 
        pk=pk
    )
    
    generator = VehicleCardPDFGenerator(vehicle)
    pdf_buffer = generator.generate()
    
    response = FileResponse(
        pdf_buffer,
        content_type='application/pdf',
        filename=f'vehicle_card_{vehicle.vin}.pdf'
    )
    
    response['Content-Disposition'] = f'inline; filename="vehicle_card_{vehicle.vin}.pdf"'
    return response


@login_required(login_url='accounts:login')
def print_preview_html(request, pk):
    """HTML print preview page"""
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('vehicle_type', 'category', 'owner'), 
        pk=pk
    )
    return render(request, 'go_data/print_preview.html', {
        'vehicle': vehicle,
        'now': timezone.now().date(),
    })