"""
Root URL configuration for the Vehicle Management System.

This module defines the main routing for:
- Django admin (masked URL)
- Account management
- Vehicle management
- Health checks
- Debug tools (development only)
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path
from django.views.generic import TemplateView


# =============================================================================
# Core URL Configuration
# =============================================================================

urlpatterns = [

    # -------------------------------------------------------------------------
    # Admin Panel (masked via settings.ADMIN_URL)
    # -------------------------------------------------------------------------
    path(f"{settings.ADMIN_URL}/", admin.site.urls),

    # -------------------------------------------------------------------------
    # Account Management
    # -------------------------------------------------------------------------
    path("accounts/", include("accounts.urls")),

    # -------------------------------------------------------------------------
    # Vehicle Management App
    # -------------------------------------------------------------------------
    path("", include("go_data.urls")),

    # -------------------------------------------------------------------------
    # Health Check Endpoint (for load balancers / uptime monitoring)
    # -------------------------------------------------------------------------
    path(
        "health/",
        TemplateView.as_view(template_name="health.html"),
        name="health_check",
    ),
]


# =============================================================================
# Security: Block common admin URL probes
# =============================================================================

blocked_admin_paths = [
    "admin/",
    "administrator/",
    "adm/",
    "backend/",
    "cpanel/",
]

urlpatterns += [
    path(p, custom_404_view) for p in blocked_admin_paths
]


# =============================================================================
# Development Tools
# =============================================================================

if settings.DEBUG:

    # Serve uploaded media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Django Debug Toolbar
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
        ]

    # Development utilities
    urlpatterns += [
        path(
            "debug/email/",
            TemplateView.as_view(template_name="debug/email_preview.html"),
            name="debug_email",
        ),
    ]


# ============================================================================
# Custom Error Handlers
# ============================================================================

handler404 = 'accounts.views.custom_404_view'      # Points to view in accounts/views.py
handler500 = 'accounts.views.custom_500_view'      # Points to view in accounts/views.py
handler403 = 'accounts.views.custom_403_view'      # Points to view in accounts/views.py
handler400 = 'accounts.views.custom_400_view'      # Points to view in accounts/views.py