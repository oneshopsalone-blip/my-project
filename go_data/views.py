"""
Vehicle management views for We Yone Pot - Digital Osusu Platform
Handles all vehicle-related views including CRUD operations, dashboard, and printing
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse, JsonResponse
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q, Max
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Prefetch

from dateutil.relativedelta import relativedelta

from .models import Vehicle, VehicleType, VehicleCategory, Owner, PrintLog
from .forms import (
    VehicleForm, VehicleTypeForm, VehicleCategoryForm, OwnerForm,
    VehicleSearchForm, VehicleRenewForm
)
from .services.pdf_generator import VehicleCardPDFGenerator

logger = logging.getLogger(__name__)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client_ip(request) -> Optional[str]:
    """
    Get client IP from request headers.
    
    Args:
        request: HTTP request object
        
    Returns:
        Client IP address string or None
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_date_filter_params(request) -> tuple:
    """
    Extract and validate date filter parameters from request.
    
    Args:
        request: HTTP request object
        
    Returns:
        Tuple of (date_from_obj, date_to_obj) as date objects or None
    """
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    date_from_obj = None
    date_to_obj = None
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.warning(f"Invalid date_from format: {date_from}")
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.warning(f"Invalid date_to format: {date_to}")
    
    return date_from_obj, date_to_obj


def handle_form_errors(request, form: Any, form_name: str = "Form") -> None:
    """
    Extract and log form errors, add error messages to request.
    
    Args:
        request: HTTP request object
        form: Django form instance with errors
        form_name: Name of the form for error messages
    """
    for field, errors in form.errors.items():
        for error in errors:
            field_name = form.fields[field].label if field in form.fields else field
            error_msg = f"{form_name} error - {field_name}: {error}"
            logger.warning(error_msg)
            messages.error(request, f"{field_name}: {error}")


def get_popular_vehicles(limit: int = 10, days: int = 30):
    """
    Get most printed vehicles in the last N days.
    
    Args:
        limit: Maximum number of vehicles to return
        days: Number of days to look back
        
    Returns:
        QuerySet of vehicles with print_count annotation
    """
    since = timezone.now() - timedelta(days=days)
    return Vehicle.objects.filter(
        print_logs__printed_at__gte=since,
        is_active=True
    ).annotate(
        print_count=Count('print_logs')
    ).order_by('-print_count')[:limit]


def get_owner_print_summary(owner_id: int, days: int = 30) -> Dict[str, Any]:
    """
    Get print summary for a specific owner.
    
    Args:
        owner_id: Owner ID
        days: Number of days to look back
        
    Returns:
        Dictionary with print statistics
    """
    since = timezone.now() - timedelta(days=days)
    return PrintLog.objects.filter(
        vehicle__owner_id=owner_id,
        printed_at__gte=since
    ).aggregate(
        total_prints=Count('id'),
        vehicles_printed=Count('vehicle', distinct=True),
        last_print=Max('printed_at')
    )


def get_today_printed_vehicles():
    """Get vehicles printed today."""
    today = timezone.now().date()
    return Vehicle.objects.filter(
        print_logs__printed_at__date=today
    ).select_related('vehicle_type', 'category', 'owner').distinct()




# ============================================================================
# DASHBOARD VIEW
# ============================================================================

class VehicleDashboardView(LoginRequiredMixin, ListView):
    """
    Dashboard view listing all vehicles with print statistics.
    Requires authentication.
    """
    model = Vehicle
    template_name = 'go_data/dashboard.html'
    context_object_name = 'vehicles'
    paginate_by = 20
    login_url = 'accounts:login'

    def get_queryset(self):
        """Apply search and filter to queryset - optionally exclude printed vehicles"""
        queryset = Vehicle.objects.select_related(
            'vehicle_type', 'category', 'owner'
        ).all()
        
        # Apply search filter
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(vehicle_reg__icontains=search) |
                Q(vin__icontains=search) |
                Q(owner__name__icontains=search) |
                Q(vehicle_type__code__icontains=search) |
                Q(vehicle_type__name__icontains=search)
            )
        
        # Apply owner filter
        owner_id = self.request.GET.get('owner')
        if owner_id and owner_id.isdigit():
            queryset = queryset.filter(owner_id=owner_id)
        
        # Apply type filter
        type_id = self.request.GET.get('type')
        if type_id and type_id.isdigit():
            queryset = queryset.filter(vehicle_type_id=type_id)
        
        # Apply category filter
        category_id = self.request.GET.get('category')
        if category_id and category_id.isdigit():
            queryset = queryset.filter(category_id=category_id)
        
        # Apply status filter
        status = self.request.GET.get('status')
        today = timezone.now().date()
        
        if status == 'active':
            queryset = queryset.filter(is_active=True, expiry_date__gte=today)
        elif status == 'expired':
            queryset = queryset.filter(is_active=True, expiry_date__lt=today)
        elif status == 'expiring_soon':
            threshold = today + timedelta(days=30)
            queryset = queryset.filter(
                is_active=True,
                expiry_date__gte=today,
                expiry_date__lte=threshold
            )
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Optionally exclude printed vehicles
        show_printed = self.request.GET.get('show_printed') == 'true'
        if not show_printed:
            printed_vehicle_ids = PrintLog.objects.filter(
                printed_at__date=timezone.now().date()
            ).values_list('vehicle_id', flat=True)
            queryset = queryset.exclude(id__in=printed_vehicle_ids)
        
        return queryset.order_by('-created_at')
    
    def get_vehicles_by_owner(self):
        """Group vehicles by owner"""
        queryset = self.get_queryset()
        
        # Get all owners with their vehicles
        owners = Owner.objects.filter(is_active=True).prefetch_related(
            Prefetch('vehicles', 
                    queryset=queryset,
                    to_attr='filtered_vehicles')
        )
        
        vehicles_by_owner = []
        for owner in owners:
            owner_vehicles = getattr(owner, 'filtered_vehicles', [])
            if owner_vehicles:  # Only include owners with vehicles
                vehicles_by_owner.append({
                    'owner': owner,
                    'vehicles': owner_vehicles,
                    'vehicle_count': len(owner_vehicles),
                    'print_count': PrintLog.objects.filter(
                        vehicle__owner=owner,
                        printed_at__date=timezone.now().date()
                    ).count()
                })
        
        return vehicles_by_owner

    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        
        today = timezone.now().date()
        
        # Get printed vehicles for today
        printed_vehicles = get_today_printed_vehicles()
        
        # Get vehicles grouped by owner
        vehicles_by_owner = self.get_vehicles_by_owner()
        
        # Get date filters
        date_from_obj, date_to_obj = get_date_filter_params(self.request)
        
        # Check if print stats should be shown
        show_print_stats = self.request.GET.get('show_stats') == 'true'
        
        # Build owners with print counts (only if stats are shown)
        owners_with_counts = []
        total_prints = 0
        
        if show_print_stats:
            owners_with_counts = self._get_owners_with_counts(date_from_obj, date_to_obj)
            total_prints = sum(o['print_count'] for o in owners_with_counts)
        
        # Get statistics
        stats = self._get_dashboard_stats(today)
        
        # Prepare filter values for template
        context.update({
            # Statistics
            **stats,
            
            # Owner data
            'owners_with_counts': owners_with_counts,
            'total_prints': total_prints,
            
            # Vehicles by owner
            'vehicles_by_owner': vehicles_by_owner,
            
            # Printed vehicles
            'printed_vehicles': printed_vehicles,
            'printed_count': printed_vehicles.count(),
            
            # Filter values
            'selected_owner_id': self.request.GET.get('owner'),
            'selected_type_id': self.request.GET.get('type'),
            'selected_category_id': self.request.GET.get('category'),
            'selected_status': self.request.GET.get('status', ''),
            'search_query': self.request.GET.get('search', ''),
            'date_from': date_from_obj,
            'date_to': date_to_obj,
            'show_print_stats': show_print_stats,
            'show_printed': self.request.GET.get('show_printed') == 'true',
            
            # Forms
            'search_form': VehicleSearchForm(self.request.GET),
            
            # Current date
            'now': today,
        })
        
        return context

    def _get_owners_with_counts(self, date_from=None, date_to=None):
        """Get owners with their print counts within date range"""
        owners = Owner.objects.filter(is_active=True)
        owners_with_counts = []
        
        for owner in owners:
            print_logs = PrintLog.objects.filter(vehicle__owner=owner)
            
            if date_from:
                print_logs = print_logs.filter(printed_at__date__gte=date_from)
            if date_to:
                print_logs = print_logs.filter(printed_at__date__lte=date_to)
            
            count = print_logs.count()
            
            owners_with_counts.append({
                'id': owner.id,
                'name': owner.name,
                'owner_id': owner.owner_id,
                'print_count': count,
                'vehicle_count': owner.vehicle_count
            })
        
        # Sort by print count (highest first)
        owners_with_counts.sort(key=lambda x: x['print_count'], reverse=True)
        return owners_with_counts
    
    def _get_dashboard_stats(self, today):
        """Get dashboard statistics"""
        total_vehicles = Vehicle.objects.count()
        active_vehicles = Vehicle.objects.filter(
            is_active=True, 
            expiry_date__gte=today
        ).count()
        expired_vehicles = Vehicle.objects.filter(
            is_active=True, 
            expiry_date__lt=today
        ).count()
        expiring_soon = Vehicle.objects.filter(
            is_active=True,
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=30)
        ).count()
        
        return {
            'total_vehicles': total_vehicles,
            'active_vehicles': active_vehicles,
            'expired_vehicles': expired_vehicles,
            'expiring_soon': expiring_soon,
            'total_types': VehicleType.objects.filter(is_active=True).count(),
            'total_categories': VehicleCategory.objects.filter(is_active=True).count(),
            'total_owners': Owner.objects.filter(is_active=True).count(),
        }


# ============================================================================
# PRINT TRACKING
# ============================================================================
@login_required(login_url='accounts:login')
@require_POST
@ensure_csrf_cookie
def track_print(request, pk):
    """
    Track when a vehicle document is printed.
    Accepts POST requests only.
    
    Args:
        request: HTTP request object
        pk: Vehicle primary key
        
    Returns:
        JSON response with tracking result
    """
    try:
        vehicle = get_object_or_404(
            Vehicle.objects.select_related('owner', 'vehicle_type'), 
            pk=pk
        )
        
        print_log = PrintLog.objects.create(
            vehicle=vehicle,
            printed_by=request.user.get_full_name() or request.user.username,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        logger.info(
            f"Print tracked: Vehicle {pk} ({vehicle.vin}) by {request.user.username}"
        )
        
        # Get updated printed count for today
        today = timezone.now().date()
        today_prints = PrintLog.objects.filter(
            printed_at__date=today
        ).values_list('vehicle_id', flat=True).distinct().count()
        
        # Get the printed vehicle data for immediate display
        printed_vehicle_data = {
            'id': vehicle.id,
            'vin': vehicle.vin,
            'vehicle_reg': vehicle.vehicle_reg,
            'vehicle_type_code': vehicle.vehicle_type.code if vehicle.vehicle_type else 'N/A',
            'owner_name': vehicle.owner.name if vehicle.owner else 'No Owner',
            'owner_id': vehicle.owner.owner_id if vehicle.owner else '',
            'last_printed': print_log.printed_at.isoformat(),
        }
        
        return JsonResponse({
            'success': True,
            'print_id': print_log.id,
            'timestamp': print_log.printed_at.isoformat(),
            'message': 'Print tracked successfully',
            'printed_count': today_prints,
            'vehicle_id': pk,
            'removed': True,
            'printed_vehicle': printed_vehicle_data,
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
@require_GET
def get_printed_vehicles(request):
    """
    API endpoint to get today's printed vehicles.
    
    Args:
        request: HTTP request object
        
    Returns:
        JSON response with printed vehicles
    """
    try:
        today = timezone.now().date()
        printed_vehicles = Vehicle.objects.filter(
            print_logs__printed_at__date=today
        ).select_related('vehicle_type', 'category', 'owner').distinct()
        
        vehicles_data = []
        for vehicle in printed_vehicles:
            last_print = vehicle.print_logs.filter(printed_at__date=today).last()
            vehicles_data.append({
                'id': vehicle.id,
                'vin': vehicle.vin,
                'vehicle_reg': vehicle.vehicle_reg,
                'vehicle_type_code': vehicle.vehicle_type.code if vehicle.vehicle_type else 'N/A',
                'owner_name': vehicle.owner.name if vehicle.owner else 'No Owner',
                'owner_id': vehicle.owner.owner_id if vehicle.owner else '',
                'category_code': vehicle.category.code if vehicle.category else '',
                'expiry_date': vehicle.expiry_date_formatted,
                'print_count': vehicle.print_logs.filter(printed_at__date=today).count(),
                'last_printed': last_print.printed_at.isoformat() if last_print else None,
            })
        
        return JsonResponse({
            'success': True,
            'vehicles': vehicles_data,
            'count': len(vehicles_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching printed vehicles: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required(login_url='accounts:login')
@require_GET
def get_print_stats(request):
    """
    API endpoint to get print statistics.
    
    Args:
        request: HTTP request object
        
    Returns:
        JSON response with print statistics
    """
    try:
        vehicle_id = request.GET.get('vehicle_id')
        owner_id = request.GET.get('owner_id')
        date_from_obj, date_to_obj = get_date_filter_params(request)
        
        queryset = PrintLog.objects.select_related('vehicle')
        
        if vehicle_id and vehicle_id.isdigit():
            queryset = queryset.filter(vehicle_id=vehicle_id)
        
        if owner_id and owner_id.isdigit():
            queryset = queryset.filter(vehicle__owner_id=owner_id)
        
        if date_from_obj:
            queryset = queryset.filter(printed_at__date__gte=date_from_obj)
        if date_to_obj:
            queryset = queryset.filter(printed_at__date__lte=date_to_obj)
        
        # Get popular vehicles
        days = int(request.GET.get('days', 30))
        popular_vehicles = get_popular_vehicles(limit=5, days=days)
        
        # Group by date
        stats_by_date = []
        try:
            from django.db.models.functions import TruncDate
            stats_by_date = queryset.annotate(
                print_date=TruncDate('printed_at')
            ).values('print_date').annotate(
                count=Count('id')
            ).order_by('-print_date')[:30]
        except Exception as e:
            logger.warning(f"Date truncation failed: {e}")
        
        return JsonResponse({
            'success': True,
            'total': queryset.count(),
            'by_date': list(stats_by_date),
            'popular_vehicles': [
                {
                    'id': v.id,
                    'vin': v.vin,
                    'vehicle_reg': v.vehicle_reg,
                    'print_count': getattr(v, 'print_count', 0),
                    'owner_name': v.owner.name if v.owner else ''
                } for v in popular_vehicles
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting print stats: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


# ============================================================================
# VEHICLE CRUD
# ============================================================================

@login_required(login_url='accounts:login')
def vehicle_create(request):
    """Create a new vehicle"""
    if request.method == 'POST':
        form = VehicleForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                vehicle = form.save()
                messages.success(
                    request, 
                    f'Vehicle {vehicle.vehicle_reg or vehicle.vin} created successfully!'
                )
                logger.info(f"Vehicle created: {vehicle.vin} by {request.user.username}")
                return redirect('go_data:dashboard')
            except (IntegrityError, ValidationError) as e:
                logger.error(f"Vehicle creation error: {str(e)}")
                messages.error(request, f'Error creating vehicle: {str(e)}')
        else:
            handle_form_errors(request, form, "Vehicle")
    else:
        form = VehicleForm(user=request.user)
    
    return render(request, 'go_data/vehicle_form.html', {
        'form': form,
        'title': 'Add New Vehicle',
        'action': 'create'
    })


@login_required(login_url='accounts:login')
def vehicle_update(request, pk):
    """Update an existing vehicle"""
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('vehicle_type', 'category', 'owner'),
        pk=pk
    )
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(
                    request, 
                    f'Vehicle {vehicle.vehicle_reg or vehicle.vin} updated successfully!'
                )
                logger.info(f"Vehicle updated: {vehicle.vin} by {request.user.username}")
                return redirect('go_data:dashboard')
            except (IntegrityError, ValidationError) as e:
                logger.error(f"Vehicle update error: {str(e)}")
                messages.error(request, f'Error updating vehicle: {str(e)}')
        else:
            handle_form_errors(request, form, "Vehicle")
    else:
        form = VehicleForm(instance=vehicle, user=request.user)
    
    # Get categories for the vehicle's type for the form
    categories = VehicleCategory.get_active_categories(vehicle_type=vehicle.vehicle_type)
    
    return render(request, 'go_data/vehicle_form.html', {
        'form': form,
        'vehicle': vehicle,
        'title': f'Edit Vehicle: {vehicle.vehicle_reg or vehicle.vin}',
        'categories': categories,
        'action': 'update'
    })


@login_required(login_url='accounts:login')
def vehicle_delete(request, pk):
    """Delete a vehicle"""
    vehicle = get_object_or_404(Vehicle, pk=pk)
    
    if request.method == 'POST':
        vehicle_name = vehicle.vehicle_reg or vehicle.vin
        
        # Check if vehicle has print logs
        has_prints = vehicle.print_logs.exists()
        
        if has_prints:
            messages.warning(
                request,
                f'Vehicle {vehicle_name} has print records. Consider deactivating instead.'
            )
            return redirect('go_data:vehicle_detail', pk=pk)
        
        try:
            vehicle.delete()
            messages.success(request, f'Vehicle {vehicle_name} deleted successfully!')
            logger.info(f"Vehicle deleted: {pk} by {request.user.username}")
        except (IntegrityError, ValidationError) as e:
            logger.error(f"Vehicle deletion error: {str(e)}")
            messages.error(request, f'Error deleting vehicle: {str(e)}')
        
        return redirect('go_data:dashboard')
    
    return render(request, 'go_data/vehicle_confirm_delete.html', {
        'vehicle': vehicle,
        'has_prints': vehicle.print_logs.exists()
    })


@login_required(login_url='accounts:login')
def vehicle_detail(request, pk):
    """View vehicle details"""
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('vehicle_type', 'category', 'owner'), 
        pk=pk
    )
    
    # Get recent print logs
    recent_prints = vehicle.print_logs.select_related().order_by('-printed_at')[:10]
    
    return render(request, 'go_data/vehicle_detail.html', {
        'vehicle': vehicle,
        'now': timezone.now().date(),
        'recent_prints': recent_prints,
        'renew_form': VehicleRenewForm(),
        'is_expired': vehicle.is_expired(),
        'days_until_expiry': vehicle.days_until_expiry(),
    })


@login_required(login_url='accounts:login')
def vehicle_renew(request, pk):
    """Renew vehicle registration"""
    vehicle = get_object_or_404(Vehicle, pk=pk)
    
    if request.method == 'POST':
        form = VehicleRenewForm(request.POST)
        if form.is_valid():
            years = form.cleaned_data['years']
            try:
                vehicle.renew(years=years)
                messages.success(
                    request,
                    f'Vehicle {vehicle.vehicle_reg or vehicle.vin} renewed for {years} year(s). '
                    f'New expiry: {vehicle.expiry_date.strftime("%m/%Y")}'
                )
                logger.info(f"Vehicle renewed: {vehicle.vin} by {request.user.username}")
                return redirect('go_data:vehicle_detail', pk=pk)
            except Exception as e:
                logger.error(f"Vehicle renewal error: {str(e)}")
                messages.error(request, f'Error renewing vehicle: {str(e)}')
        else:
            handle_form_errors(request, form, "Renewal")
    else:
        form = VehicleRenewForm()
    
    return render(request, 'go_data/vehicle_renew.html', {
        'vehicle': vehicle,
        'form': form
    })


# ============================================================================
# VEHICLE TYPE CRUD
# ============================================================================
@login_required(login_url='accounts:login')
def vehicle_type_list(request):
    """List all vehicle types"""
    types = VehicleType.objects.annotate(
        vehicle_count=Count('vehicles'),
        category_count=Count('categories')
    ).all()
    return render(request, 'go_data/vehicle_type_list.html', {'types': types})


@login_required(login_url='accounts:login')
def vehicle_type_create(request):
    """Create a new vehicle type"""
    if request.method == 'POST':
        form = VehicleTypeForm(request.POST)
        if form.is_valid():
            try:
                vehicle_type = form.save()
                messages.success(
                    request, 
                    f'Vehicle type {vehicle_type.code} created successfully!'
                )
                logger.info(f"Vehicle type created: {vehicle_type.code}")
                return redirect('go_data:vehicle_type_list')
            except (IntegrityError, ValidationError) as e:
                logger.error(f"Vehicle type creation error: {str(e)}")
                messages.error(request, f'Error creating vehicle type: {str(e)}')
        else:
            handle_form_errors(request, form, "Vehicle Type")
    else:
        form = VehicleTypeForm()
    
    return render(request, 'go_data/vehicle_type_form.html', {
        'form': form,
        'title': 'Add Vehicle Type',
        'action': 'create'
    })


@login_required(login_url='accounts:login')
def vehicle_type_update(request, pk):
    """Update a vehicle type"""
    vehicle_type = get_object_or_404(VehicleType, pk=pk)
    
    if request.method == 'POST':
        form = VehicleTypeForm(request.POST, instance=vehicle_type)
        if form.is_valid():
            try:
                form.save()
                messages.success(
                    request, 
                    f'Vehicle type {vehicle_type.code} updated successfully!'
                )
                logger.info(f"Vehicle type updated: {vehicle_type.code}")
                return redirect('go_data:vehicle_type_list')
            except (IntegrityError, ValidationError) as e:
                logger.error(f"Vehicle type update error: {str(e)}")
                messages.error(request, f'Error updating vehicle type: {str(e)}')
        else:
            handle_form_errors(request, form, "Vehicle Type")
    else:
        form = VehicleTypeForm(instance=vehicle_type)
    
    return render(request, 'go_data/vehicle_type_form.html', {
        'form': form,
        'object': vehicle_type,
        'title': f'Edit Vehicle Type: {vehicle_type.code}',
        'action': 'update'
    })


@login_required(login_url='accounts:login')
def vehicle_type_delete(request, pk):
    """Delete a vehicle type"""
    vehicle_type = get_object_or_404(VehicleType, pk=pk)
    
    if request.method == 'POST':
        if vehicle_type.vehicles.exists():
            messages.error(
                request, 
                f'Cannot delete {vehicle_type.code} because it has {vehicle_type.vehicles.count()} vehicles assigned.'
            )
            return redirect('go_data:vehicle_type_list')
        
        try:
            vehicle_type.delete()
            messages.success(
                request, 
                f'Vehicle type {vehicle_type.code} deleted successfully!'
            )
            logger.info(f"Vehicle type deleted: {vehicle_type.code}")
        except (IntegrityError, ValidationError) as e:
            logger.error(f"Vehicle type deletion error: {str(e)}")
            messages.error(request, f'Error deleting vehicle type: {str(e)}')
        
        return redirect('go_data:vehicle_type_list')
    
    return render(request, 'go_data/vehicle_type_confirm_delete.html', {
        'object': vehicle_type,
        'vehicle_count': vehicle_type.vehicles.count(),
        'category_count': vehicle_type.categories.count()
    })


# ============================================================================
# VEHICLE CATEGORY CRUD
# ============================================================================

@login_required(login_url='accounts:login')
# ============================================================================
# VEHICLE CATEGORY CRUD
# ============================================================================

@login_required(login_url='accounts:login')
def vehicle_category_list(request):
    """List all vehicle categories"""
    vehicle_types = VehicleType.get_active_types()
    categories = VehicleCategory.objects.select_related(
        'vehicle_type'
    ).annotate(
        vehicle_count=Count('vehicles')
    ).all()
    
    return render(request, 'go_data/vehicle_category_list.html', {
        'categories': categories,
        'vehicle_types': vehicle_types,
        'total_vehicles': Vehicle.objects.count(),
    })


@login_required(login_url='accounts:login')
def vehicle_category_create(request):
    """Create a new vehicle category"""
    # Get active vehicle types for the template
    vehicle_types = VehicleType.get_active_types()
    
    if request.method == 'POST':
        form = VehicleCategoryForm(request.POST)
        if form.is_valid():
            try:
                # Create category but don't save yet
                category = form.save(commit=False)
                # Explicitly set active status
                category.is_active = True
                # Now save
                category.save()
                
                messages.success(
                    request, 
                    f'Category {category.code} created successfully for {category.vehicle_type.name}!'
                )
                logger.info(f"Vehicle category created: {category.code} by {request.user.username}")
                return redirect('go_data:vehicle_category_list')
            except (IntegrityError, ValidationError) as e:
                logger.error(f"Vehicle category creation error: {str(e)}")
                messages.error(request, f'Error creating category: {str(e)}')
        else:
            handle_form_errors(request, form, "Vehicle Category")
    else:
        form = VehicleCategoryForm()
    
    # Calculate any additional context
    total_vehicles = Vehicle.objects.count()
    
    return render(request, 'go_data/vehicle_category_form.html', {
        'form': form,
        'vehicle_types': vehicle_types,
        'title': 'Add Vehicle Category',
        'action': 'create',
        'total_vehicles': total_vehicles,  # Optional: for summary stats
    })

@login_required(login_url='accounts:login')
def vehicle_category_update(request, pk):
    """Update a vehicle category"""
    # Get the category with related vehicle_type for efficiency
    category = get_object_or_404(
        VehicleCategory.objects.select_related('vehicle_type'), 
        pk=pk
    )
    
    # Get active vehicle types for the template
    vehicle_types = VehicleType.get_active_types()
    
    if request.method == 'POST':
        form = VehicleCategoryForm(request.POST, instance=category)
        if form.is_valid():
            try:
                updated_category = form.save()
                messages.success(
                    request, 
                    f'Category {updated_category.code} updated successfully!'
                )
                logger.info(f"Vehicle category updated: {updated_category.code} by {request.user.username}")
                return redirect('go_data:vehicle_category_list')
            except (IntegrityError, ValidationError) as e:
                logger.error(f"Vehicle category update error: {str(e)}")
                messages.error(request, f'Error updating category: {str(e)}')
        else:
            handle_form_errors(request, form, "Vehicle Category")
    else:
        form = VehicleCategoryForm(instance=category)
        
        # Pre-select the current vehicle type in the form
        if category.vehicle_type:
            form.fields['vehicle_type'].initial = category.vehicle_type.id
    
    # Calculate additional context data
    vehicle_count = category.vehicles.count()
    
    return render(request, 'go_data/vehicle_category_form.html', {
        'form': form,
        'vehicle_types': vehicle_types,
        'object': category,
        'title': f'Edit Category: {category.code}',
        'action': 'update',
        'vehicle_count': vehicle_count,
        'can_delete': vehicle_count == 0,  # Helper for template
    })

@login_required(login_url='accounts:login')
def vehicle_category_delete(request, pk):
    """Delete a vehicle category"""
    category = get_object_or_404(VehicleCategory, pk=pk)
    
    if request.method == 'POST':
        if category.vehicles.exists():
            messages.error(
                request, 
                f'Cannot delete {category.code} because it has {category.vehicles.count()} vehicles assigned.'
            )
            return redirect('go_data:vehicle_category_list')
        
        try:
            category_code = category.code
            category.delete()
            messages.success(
                request, 
                f'Category {category_code} deleted successfully!'
            )
            logger.info(f"Vehicle category deleted: {category_code}")
        except (IntegrityError, ValidationError) as e:
            logger.error(f"Vehicle category deletion error: {str(e)}")
            messages.error(request, f'Error deleting category: {str(e)}')
        
        return redirect('go_data:vehicle_category_list')
    
    return render(request, 'go_data/vehicle_category_confirm_delete.html', {
        'object': category,
        'vehicle_count': category.vehicles.count()
    })


# ============================================================================
# OWNER CRUD
# ============================================================================

@login_required(login_url='accounts:login')
def owner_list(request):
    """List all owners"""
    owners = Owner.objects.annotate(
        vehicles_count=Count('vehicles'),  # Changed from vehicle_count
        prints_count=Count('vehicles__print_logs')  # Changed from print_count
    ).all()
    
    # Get total statistics
    total_vehicles = Vehicle.objects.count()
    total_prints = PrintLog.objects.count()
    active_owners = owners.filter(is_active=True).count()
    
    return render(request, 'go_data/owner_list.html', {
        'owners': owners,
        'total_vehicles': total_vehicles,
        'total_prints': total_prints,
        'active_owners': active_owners,
    })


@login_required(login_url='accounts:login')
def owner_create(request):
    """Create a new owner"""
    if request.method == 'POST':
        form = OwnerForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                owner = form.save()
                messages.success(
                    request, 
                    f'Owner {owner.owner_id} - {owner.name} created successfully!'
                )
                logger.info(f"Owner created: {owner.owner_id} by {request.user.username}")
                return redirect('go_data:owner_list')
            except (IntegrityError, ValidationError) as e:
                logger.error(f"Owner creation error: {str(e)}")
                messages.error(request, f'Error creating owner: {str(e)}')
        else:
            handle_form_errors(request, form, "Owner")
    else:
        form = OwnerForm(user=request.user)
    
    return render(request, 'go_data/owner_form.html', {
        'form': form,
        'title': 'Add Owner',
        'action': 'create'
    })


@login_required(login_url='accounts:login')
def owner_update(request, pk):
    """Update an owner"""
    owner = get_object_or_404(Owner, pk=pk)
    
    if request.method == 'POST':
        form = OwnerForm(request.POST, instance=owner, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Owner {owner.name} updated successfully!')
                logger.info(f"Owner updated: {owner.owner_id} by {request.user.username}")
                return redirect('go_data:owner_list')
            except (IntegrityError, ValidationError) as e:
                logger.error(f"Owner update error: {str(e)}")
                messages.error(request, f'Error updating owner: {str(e)}')
        else:
            handle_form_errors(request, form, "Owner")
    else:
        form = OwnerForm(instance=owner, user=request.user)
    
    # Get print statistics for this owner
    print_summary = get_owner_print_summary(pk, days=365)
    
    return render(request, 'go_data/owner_form.html', {
        'form': form,
        'object': owner,
        'title': f'Edit Owner: {owner.name}',
        'print_summary': print_summary,
        'action': 'update'
    })


@login_required(login_url='accounts:login')
def owner_delete(request, pk):
    """Delete an owner"""
    owner = get_object_or_404(Owner, pk=pk)
    
    if request.method == 'POST':
        vehicle_count = owner.vehicles.count()
        if vehicle_count > 0:
            messages.error(
                request, 
                f'Cannot delete {owner.name} because they have {vehicle_count} vehicle(s) assigned.'
            )
            return redirect('go_data:owner_list')
        
        try:
            owner_name = owner.name
            owner.delete()
            messages.success(request, f'Owner {owner_name} deleted successfully!')
            logger.info(f"Owner deleted: {owner.owner_id} by {request.user.username}")
        except (IntegrityError, ValidationError) as e:
            logger.error(f"Owner deletion error: {str(e)}")
            messages.error(request, f'Error deleting owner: {str(e)}')
        
        return redirect('go_data:owner_list')
    
    return render(request, 'go_data/owner_confirm_delete.html', {
        'object': owner,
        'vehicle_count': owner.vehicles.count()
    })


@login_required(login_url='accounts:login')
def owner_detail(request, pk):
    """View owner details with their vehicles"""
    owner = get_object_or_404(Owner, pk=pk)
    vehicles = owner.vehicles.select_related('vehicle_type', 'category').all()
    
    # Get print statistics
    print_summary = get_owner_print_summary(pk, days=365)
    
    return render(request, 'go_data/owner_detail.html', {
        'owner': owner,
        'vehicles': vehicles,
        'print_summary': print_summary,
        'now': timezone.now().date()
    })


# ============================================================================
# API ENDPOINTS
# ============================================================================

@login_required(login_url='accounts:login')
@require_GET
def get_categories_by_type(request):
    """
    API endpoint to get categories for a specific vehicle type.
    Used for dynamic dropdowns.
    
    Args:
        request: HTTP request object with vehicle_type_id parameter
        
    Returns:
        JSON response with list of categories
    """
    vehicle_type_id = request.GET.get('vehicle_type_id')
    
    if not vehicle_type_id or not vehicle_type_id.isdigit():
        return JsonResponse({
            'success': False,
            'error': 'Invalid vehicle_type_id'
        }, status=400)
    
    try:
        vehicle_type = VehicleType.objects.get(pk=vehicle_type_id, is_active=True)
        categories = VehicleCategory.get_active_categories(vehicle_type=vehicle_type)
        
        data = [
            {
                'id': cat.id,
                'code': cat.code,
                'name': cat.name or cat.code,
                'display': str(cat)
            }
            for cat in categories
        ]
        
        return JsonResponse({
            'success': True,
            'categories': data
        })
        
    except VehicleType.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Vehicle type not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


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
    
    try:
        generator = VehicleCardPDFGenerator(vehicle)
        pdf_buffer = generator.generate()
        
        # Track the print
        PrintLog.objects.create(
            vehicle=vehicle,
            printed_by=request.user.get_full_name() or request.user.username,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        filename = f'vehicle_card_{vehicle.vin}_{timezone.now().strftime("%Y%m%d")}.pdf'
        
        response = FileResponse(
            pdf_buffer,
            content_type='application/pdf',
            filename=filename
        )
        
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"PDF generation error for vehicle {pk}: {str(e)}")
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('go_data:vehicle_detail', pk=pk)


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
        'print_time': timezone.now()
    })