from django.urls import path
from . import views

urlpatterns = [
    path('setup-2fa/', views.setup_2fa, name='setup_2fa'),
    path('verify-2fa/', views.verify_2fa, name='verify_2fa'),
    path('enable-2fa/', views.enable_2fa, name='enable_2fa'),
    path('check-status/', views.check_2fa_status, name='check_2fa_status'),
    path('access-logs/', views.access_logs, name='access_logs'),
    path('health/', views.health_check, name='health_check'),
]