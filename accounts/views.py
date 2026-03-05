"""
Account management views for We Yone Pot - Digital Osusu Platform
Handles authentication, profile management, and user sessions
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.db import IntegrityError
from django.views.generic import TemplateView
import secrets
import json
import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from .models import User, LoginHistory, UserActivity, UserSession
from .forms import (
    CustomAuthenticationForm,
    CustomUserCreationForm,
    CustomUserChangeForm,
    PasswordChangeForm,
    ProfileUpdateForm
)
from .decorators import superuser_required, prevent_double_login, ajax_required

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client_ip(request) -> str:
    """
    Extract client IP address from request.
    
    Args:
        request: HttpRequest object
        
    Returns:
        String containing client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def create_activity_log(
    user: User,
    activity_type: str,
    request,
    description: str,
    data: Optional[Dict] = None
) -> UserActivity:
    """
    Helper function to create user activity logs.
    
    Args:
        user: User instance
        activity_type: Type of activity
        request: HttpRequest object
        description: Activity description
        data: Optional JSON-serializable data
        
    Returns:
        Created UserActivity instance
    """
    return UserActivity.objects.create(
        user=user,
        activity_type=activity_type,
        ip_address=get_client_ip(request),
        description=description,
        data=data
    )


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

@never_cache
@prevent_double_login
def login_view(request):
    """
    Handle user login with security features.
    
    GET: Display login form
    POST: Authenticate user and create session
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Log attempt (without password)
        logger.info(f"Login attempt for user: {username} from IP: {get_client_ip(request)}")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check superuser status
            if user.is_superuser:
                # Check if account is locked
                can_login, message = user.can_login()
                if not can_login:
                    messages.error(request, message)
                    logger.warning(f"Locked account login attempt: {username}")
                    return render(request, 'accounts/login.html')
                
                # Perform login
                login(request, user)
                
                # Record successful login
                user.record_login(request)
                
                # Create login history
                LoginHistory.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    session_key=request.session.session_key,
                    login_successful=True
                )
                
                # Create activity log
                create_activity_log(
                    user, 'login', request,
                    f"Logged in from {get_client_ip(request)}"
                )
                
                messages.success(request, f"Welcome back, {user.get_full_name() or user.email}!")
                logger.info(f"Successful login: {username}")
                
                # Handle remember me
                if not request.POST.get('remember_me'):
                    request.session.set_expiry(0)
                
                # Redirect to next URL or dashboard
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('go_data:dashboard')
            else:
                messages.error(request, "Access denied. Admin privileges required.")
                logger.warning(f"Non-superuser login attempt: {username}")
                
                # Record failed attempt
                try:
                    failed_user = User.objects.get(email=username)
                    failed_user.record_failed_login()
                except User.DoesNotExist:
                    pass
        else:
            messages.error(request, "Invalid email or password.")
            logger.warning(f"Failed login attempt for: {username}")
    
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """
    Handle user logout and cleanup.
    """
    user = request.user
    
    # Update login history
    LoginHistory.objects.filter(
        user=user,
        session_key=request.session.session_key
    ).update(logout_time=timezone.now())
    
    # Create activity log
    create_activity_log(
        user, 'logout', request,
        f"Logged out from {get_client_ip(request)}"
    )
    
    # Update session records
    UserSession.objects.filter(
        user=user,
        session_key=request.session.session_key
    ).update(is_active=False)
    
    # Clear session
    request.session.flush()
    logout(request)
    
    messages.success(request, "You have been successfully logged out.")
    logger.info(f"User logged out: {user.email}")
    
    return redirect('accounts:login')


# ============================================================================
# PROFILE MANAGEMENT VIEWS
# ============================================================================

@login_required
def profile_view(request):
    """
    Display user profile with recent activity and login history.
    """
    # Get recent activities
    recent_activities = UserActivity.objects.filter(
        user=request.user
    ).select_related('user')[:10]
    
    # Get login history
    login_history = LoginHistory.objects.filter(
        user=request.user
    )[:10]
    
    # Get active sessions
    active_sessions = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).count()
    
    context = {
        'user': request.user,
        'recent_activities': recent_activities,
        'login_history': login_history,
        'active_sessions': active_sessions,
        'page_title': 'My Profile',
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_update(request):
    """
    Update user profile information.
    """
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            
            # Create activity log
            create_activity_log(
                request.user, 'update', request,
                "Profile updated",
                data=form.cleaned_data
            )
            
            messages.success(request, "Profile updated successfully!")
            logger.info(f"Profile updated for user: {request.user.email}")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile_update.html', {
        'form': form,
        'page_title': 'Update Profile'
    })


@login_required
def change_password(request):
    """
    Change user password with validation.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            
            # Update session to prevent logout
            update_session_auth_hash(request, user)
            
            # Create activity log
            create_activity_log(
                user, 'update', request,
                "Password changed"
            )
            
            messages.success(request, "Password changed successfully!")
            logger.info(f"Password changed for user: {user.email}")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {
        'form': form,
        'page_title': 'Change Password'
    })


# ============================================================================
# ACTIVITY AND SESSION MANAGEMENT
# ============================================================================

@login_required
def activity_log(request):
    """
    Display detailed user activity log.
    """
    activities = UserActivity.objects.filter(
        user=request.user
    ).select_related('user')[:100]
    
    return render(request, 'accounts/activity_log.html', {
        'activities': activities,
        'page_title': 'Activity Log'
    })


@login_required
def sessions_view(request):
    """
    View and manage active user sessions.
    """
    current_session_key = request.session.session_key
    
    # Update current session
    UserSession.objects.update_or_create(
        session_key=current_session_key,
        defaults={
            'user': request.user,
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
            'is_active': True,
            'last_activity': timezone.now()
        }
    )
    
    # Get other active sessions
    active_sessions = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).exclude(session_key=current_session_key)
    
    if request.method == 'POST':
        session_key = request.POST.get('session_key')
        if session_key:
            UserSession.objects.filter(
                user=request.user,
                session_key=session_key
            ).delete()
            messages.success(request, "Session terminated successfully!")
            
            create_activity_log(
                request.user, 'update', request,
                f"Terminated session: {session_key[:8]}..."
            )
            
            return redirect('accounts:sessions')
    
    context = {
        'current_session': UserSession.objects.filter(
            session_key=current_session_key
        ).first(),
        'other_sessions': active_sessions,
        'page_title': 'Active Sessions'
    }
    return render(request, 'accounts/sessions.html', context)


@require_POST
@login_required
def terminate_all_sessions(request):
    """
    Terminate all other active sessions.
    """
    current_key = request.session.session_key
    
    # Get count of terminated sessions
    terminated = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).exclude(session_key=current_key).update(is_active=False)
    
    create_activity_log(
        request.user, 'update', request,
        f"Terminated {terminated} other session(s)"
    )
    
    messages.success(request, f"All other sessions terminated successfully!")
    logger.info(f"User {request.user.email} terminated {terminated} other sessions")
    
    return redirect('accounts:sessions')


# ============================================================================
# SECURITY SETTINGS
# ============================================================================

@require_POST
@login_required
def toggle_2fa(request):
    """
    Toggle two-factor authentication setting.
    """
    user = request.user
    user.two_factor_enabled = not user.two_factor_enabled
    user.save()
    
    status = "enabled" if user.two_factor_enabled else "disabled"
    
    create_activity_log(
        user, 'update', request,
        f"Two-factor authentication {status}"
    )
    
    messages.success(request, f"Two-factor authentication {status}!")
    
    return JsonResponse({
        'success': True,
        'enabled': user.two_factor_enabled,
        'status': status
    })


# ============================================================================
# PASSWORD RESET VIEWS
# ============================================================================

class CustomPasswordResetView(PasswordResetView):
    """
    Custom password reset view with activity logging.
    """
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        
        try:
            user = User.objects.get(email=email)
            create_activity_log(
                user, 'update', self.request,
                "Password reset requested"
            )
            logger.info(f"Password reset requested for: {email}")
        except User.DoesNotExist:
            logger.info(f"Password reset requested for non-existent email: {email}")
        
        messages.success(
            self.request,
            "If an account exists with this email, you will receive password reset instructions."
        )
        
        return super().form_valid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Custom password reset confirmation view.
    """
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log successful password reset
        try:
            user = form.user
            create_activity_log(
                user, 'update', self.request,
                "Password reset completed"
            )
            logger.info(f"Password reset completed for user: {user.email}")
        except:
            pass
        
        messages.success(self.request, "Password reset successfully! Please login.")
        return response


# ============================================================================
# API ENDPOINTS
# ============================================================================

@login_required
@ajax_required
def api_get_user_info(request):
    """
    API endpoint to get current user information.
    """
    user = request.user
    
    data = {
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'user_id': user.user_id,
        'role': user.role,
        'role_display': user.get_role_display(),
        'two_factor_enabled': user.two_factor_enabled,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        'permissions': {
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
        }
    }
    
    return JsonResponse({'success': True, 'data': data})


def check_session(request):
    """
    Public endpoint to check if session is valid.
    Used by frontend for session management.
    """
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'email': request.user.email,
                'name': request.user.full_name,
                'role': request.user.role,
                'user_id': request.user.user_id,
            },
            'session_age': request.session.get_expiry_age(),
        })
    
    return JsonResponse({
        'authenticated': False
    }, status=401)


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================

@login_required
def dashboard_redirect(request):
    """
    Redirect authenticated users to the main dashboard.
    """
    return redirect('go_data:dashboard')


# Optional: Simple dashboard view if needed
class AccountDashboardView(TemplateView):
    """
    Account management dashboard.
    """
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['active_sessions'] = UserSession.objects.filter(
            user=self.request.user,
            is_active=True
        ).count()
        context['recent_activities'] = UserActivity.objects.filter(
            user=self.request.user
        )[:5]
        return context
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


"""
Custom error views for the project.
"""

from django.shortcuts import render

# ============================================================================
# Custom Error Views
# ============================================================================

def custom_404_view(request, exception=None):
    """Custom 404 page"""
    return render(request, '404.html', status=404)

def custom_500_view(request):
    """Custom 500 Internal Server Error page"""
    return render(request, '500.html', status=500)

def custom_403_view(request, exception=None):
    """Custom 403 Forbidden page"""
    return render(request, '403.html', status=403)

def custom_400_view(request, exception=None):
    """Custom 400 Bad Request page"""
    return render(request, '400.html', status=400)

