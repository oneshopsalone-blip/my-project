from django.urls import path
from . import views

app_name = 'go_data'  # or 'vehicles' - be consistent!

urlpatterns = [
    path('', views.VehicleDashboardView.as_view(), name='dashboard'),
    path('vehicle/create/', views.vehicle_create, name='vehicle_create'),
    path('vehicle/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicle/<int:pk>/update/', views.vehicle_update, name='vehicle_update'),
    path('vehicle/<int:pk>/delete/', views.vehicle_delete, name='vehicle_delete'),
    
    # Vehicle Type URLs
    path('types/', views.vehicle_type_list, name='vehicle_type_list'),
    path('types/create/', views.vehicle_type_create, name='vehicle_type_create'),
    path('types/<int:pk>/update/', views.vehicle_type_update, name='vehicle_type_update'),
    path('types/<int:pk>/delete/', views.vehicle_type_delete, name='vehicle_type_delete'),
    
    # Vehicle Category URLs
    path('categories/', views.vehicle_category_list, name='vehicle_category_list'),
    path('categories/create/', views.vehicle_category_create, name='vehicle_category_create'),
    path('categories/<int:pk>/update/', views.vehicle_category_update, name='vehicle_category_update'),
    path('categories/<int:pk>/delete/', views.vehicle_category_delete, name='vehicle_category_delete'),
    
    # Owner URLs
    path('owners/', views.owner_list, name='owner_list'),
    path('owners/create/', views.owner_create, name='owner_create'),
    path('owners/<int:pk>/update/', views.owner_update, name='owner_update'),
    path('owners/<int:pk>/delete/', views.owner_delete, name='owner_delete'),
    
    # Print URLs
    path('vehicle/<int:pk>/print/', views.print_vehicle_card, name='print_card'),
    path('vehicle/<int:pk>/print-preview/', views.print_preview_html, name='print_preview'),
    path('vehicle/<int:pk>/track-print/', views.track_print, name='track_print'),
    path('api/print-stats/', views.get_print_stats, name='print_stats'),
]