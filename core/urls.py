from django.urls import path
from . import views

urlpatterns = [
    path("devices/", views.device_list, name="device_list"),
    path("devices/<int:device_id>/", views.device_detail, name="device_detail"),
    path("", views.dashboard, name="dashboard"),
    path("measurements/", views.measurement_list, name="measurement_list"),  
    path("alerts/", views.alert_list, name="alert_list"),   
    path('login/', views.login_view, name='login'),        
    path('register/', views.register_view, name='register'),  
]