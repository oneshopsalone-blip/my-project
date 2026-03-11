"""
Custom decorators for access control and permission checking
"""

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from functools import wraps
from typing import Callable, Optional, Any

from django.http import JsonResponse

# ============================================================================
# CUSTOM DECORATORS
# ============================================================================

def superuser_required(view_func: Callable) -> Callable:
    """
    Decorator to ensure user is authenticated and is a superuser.
    
    Args:
        view_func: The view function to decorate
        
    Returns:
        Wrapped view function that checks superuser status
        
    Example:
        @superuser_required
        def admin_dashboard(request):
            return render(request, 'admin/dashboard.html')
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check authentication
        if not request.user.is_authenticated:
            messages.warning(request, "Please login to access this page.")
            return redirect('accounts:login')
        
        # Check superuser status
        if not request.user.is_superuser:
            messages.error(
                request, 
                "Access denied. This area requires administrator privileges."
            )
            
            # Log unauthorized access attempt
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Unauthorized access attempt by {request.user.email} "
                f"to {request.path}"
            )
            
            return redirect('go_data:dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def admin_required(
    function: Optional[Callable] = None,
    redirect_field_name: str = 'next',
    login_url: str = 'accounts:login'
) -> Callable:
    """
    Decorator for views that checks if the user is an active superuser.
    Uses Django's built-in user_passes_test decorator.
    
    Args:
        function: The view function to decorate
        redirect_field_name: Name of the field to store redirect URL
        login_url: URL to redirect unauthenticated users
        
    Returns:
        Decorated view function
        
    Example:
        @admin_required
        def sensitive_view(request):
            return render(request, 'sensitive.html')
    """
    def test_func(user):
        return user.is_authenticated and user.is_active and user.is_superuser
    
    actual_decorator = user_passes_test(
        test_func,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    
    if function:
        return actual_decorator(function)
    return actual_decorator


def staff_required(view_func: Callable) -> Callable:
    """
    Decorator to ensure user is authenticated and is staff.
    Staff users have some admin privileges but not full superuser access.
    
    Args:
        view_func: The view function to decorate
        
    Returns:
        Wrapped view function that checks staff status
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please login to access this page.")
            return redirect('accounts:login')
        
        if not request.user.is_staff:
            messages.error(request, "Access denied. Staff privileges required.")
            return redirect('go_data:dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def role_required(allowed_roles: list) -> Callable:
    """
    Decorator factory to check if user has one of the allowed roles.
    
    Args:
        allowed_roles: List of role names that are allowed access
        
    Returns:
        Decorator function that checks user role
        
    Example:
        @role_required(['admin', 'manager'])
        def manager_view(request):
            return render(request, 'manager/dashboard.html')
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please login to access this page.")
                return redirect('accounts:login')
            
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                messages.error(
                    request, 
                    f"Access denied. This area requires one of these roles: "
                    f"{', '.join(allowed_roles)}"
                )
                return redirect('go_data:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator


def ajax_required(view_func: Callable) -> Callable:
    """
    Decorator to ensure request is AJAX.
    
    Args:
        view_func: The view function to decorate
        
    Returns:
        Wrapped view function that checks for AJAX request
        
    Example:
        @ajax_required
        def ajax_endpoint(request):
            return JsonResponse({'status': 'success'})
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(
                {'error': 'This endpoint only accepts AJAX requests'},
                status=400
            )
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def prevent_double_login(view_func: Callable) -> Callable:
    """
    Decorator to prevent users from accessing login page if already authenticated.
    
    Args:
        view_func: The view function to decorate
        
    Returns:
        Wrapped view function that redirects authenticated users
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You are already logged in.")
            return redirect('go_data:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view