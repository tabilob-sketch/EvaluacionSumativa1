from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("devices/", views.device_list, name="device_list"),
    path("devices/<int:device_id>/", views.device_detail, name="device_detail"),

    path("measurements/", views.measurement_list, name="measurement_list"),
    path("alerts/", views.alert_list, name="alert_list"),
    path("alerts/week/", views.alerts_week, name="alerts_week"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("password-reset/", views.password_reset_view, name="password_reset"),
]
