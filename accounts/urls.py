"""
Account management URL configuration for We Yone Pot - Digital Osusu Platform
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from . import views

app_name = 'accounts'

# ============================================================================
# URL Patterns
# ============================================================================

urlpatterns = [
    # ------------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------------
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ------------------------------------------------------------------------
    # Password Reset Flow
    # ------------------------------------------------------------------------
    # 1. Request password reset
    path('password-reset/', 
         views.CustomPasswordResetView.as_view(), 
         name='password_reset'),
    
    # 2. Email sent confirmation
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    # 3. Link from email (set new password)
    path('password-reset/<uidb64>/<token>/', 
         views.CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    
    # 4. Password reset complete
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # ------------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------------
    # Main profile
    path('profile/', views.profile_view, name='profile'),
    
    # Profile actions
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Activity and sessions
    path('profile/activities/', views.activity_log, name='activity_log'),
    path('profile/sessions/', views.sessions_view, name='sessions'),
    path('profile/sessions/terminate-all/', 
         views.terminate_all_sessions, 
         name='terminate_sessions'),
    
    # Security settings
    path('profile/toggle-2fa/', views.toggle_2fa, name='toggle_2fa'),
    
    # ------------------------------------------------------------------------
    # Dashboard & Overview
    # ------------------------------------------------------------------------
    path('dashboard/', 
         views.AccountDashboardView.as_view(), 
         name='dashboard'),
    
    # ------------------------------------------------------------------------
    # API Endpoints (JSON responses)
    # ------------------------------------------------------------------------
    path('api/user-info/', views.api_get_user_info, name='api_user_info'),
    path('api/check-session/', views.check_session, name='check_session'),
]


# ============================================================================
# Optional: Include these if you need additional functionality
# ============================================================================

# Account registration (if needed in future)
# path('register/', views.register_view, name='register'),
# path('register/complete/', views.register_complete, name='register_complete'),

# Email verification (if needed in future)
# path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
# path('resend-verification/', views.resend_verification, name='resend_verification'),