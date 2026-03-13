from django.urls import path
from . import views

app_name = "tickets"   # ✅ Added namespace

urlpatterns = [
    # Manual Complaint
    path('report/', views.qr_complaint_view, name='manual_complaint'),

    # QR Complaint
    path('q/<str:token>/', views.qr_complaint_view, name='qr_complaint'),

    # Notification API
    path('api/check-notifications/', views.check_new_tickets, name='check_notifications'),

    # Emergency Page
    path('emergency/', views.emergency_view, name='emergency'),
]