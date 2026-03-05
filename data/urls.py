"""
Main URL configuration for Vehicle Management System.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.shortcuts import render

# ============================================================================
# Custom Error Views
# ============================================================================

def custom_404_view(request, exception=None):
    """Custom 404 page"""
    return render(request, 'accounts/404.html', status=404)

def custom_500_view(request):
    """Custom 500 page"""
    return render(request, 'accounts/500.html', status=500)

def custom_403_view(request, exception=None):
    """Custom 403 page"""
    return render(request, 'accounts/403.html', status=403)




# ============================================================================
# Main URL Patterns
# ============================================================================

urlpatterns = [
    # Masked admin URL
    path(f'{settings.ADMIN_URL}/', admin.site.urls),
    
    # Account Management
    path('accounts/', include('accounts.urls')),
    
    # Vehicle Management
    path('', include('go_data.urls')),
    
]

# ============================================================================
# Security: Redirect old admin paths to 404
# ============================================================================

blocked_admin_paths = [
    'admin/',
    'admin/login/',
    'admin/logout/',
    'admin/password_change/',
    'admin/password_reset/',
    'administrator/',
    'adm/',
    'backend/',
    'cpanel/',
    'wp-admin/',
    'dashboard/',
]

urlpatterns += [
    path(p, custom_404_view) for p in blocked_admin_paths
]

# Explicit 404 page
urlpatterns += [
    path('404/', TemplateView.as_view(template_name='404.html'), name='404'),
]

# ============================================================================
# Debug Tools (only in development)
# ============================================================================

if settings.DEBUG:
    # Serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

# ============================================================================
# Custom Error Handlers
# ============================================================================

handler404 = 'data.urls.custom_404_view'
handler500 = 'data.urls.custom_500_view'
handler403 = 'data.urls.custom_403_view'

from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError

def health_check(request):
    """Health check endpoint to verify database connection"""
    status = "healthy"
    db_status = "connected"
    
    # Check database connection
    try:
        connections['default'].cursor()
    except OperationalError:
        db_status = "disconnected"
        status = "unhealthy"
    
    return JsonResponse({
        'status': status,
        'database': db_status,
        'debug': settings.DEBUG,
        'allowed_hosts': settings.ALLOWED_HOSTS,
    })

urlpatterns += [
    path('health/', health_check, name='health_check'),
]