"""
Custom error handlers for the main application.
"""

from django.shortcuts import render


def custom_500_view(request):
    """Custom 500 Internal Server Error page"""
    return render(request, '500.html', status=500)


def custom_403_view(request, exception=None):
    """Custom 403 Forbidden page"""
    return render(request, '403.html', status=403)
