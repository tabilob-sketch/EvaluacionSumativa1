# core/urls.py
from django.urls import path
from . import views          # vistas generales (dashboard, auth, perfil, etc.)
from . import device_views   # vistas del CRUD de Device

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Dispositivos (CRUD)
    path("devices/", device_views.device_list, name="device_list"),
    path("devices/<int:device_id>/", device_views.device_detail, name="device_detail"),
    path("devices/create/", device_views.device_create, name="device_create"),
    path("devices/<int:device_id>/edit/", device_views.device_update, name="device_update"),
    path("devices/<int:device_id>/delete/", device_views.device_delete, name="device_delete"),
    path("devices/export/", device_views.device_export, name="device_export"),

    # Measurements / Alerts
    path("measurements/", views.measurement_list, name="measurement_list"),
    path("alerts/", views.alert_list, name="alert_list"),
    path("alerts/week/", views.alerts_week, name="alerts_week"),

    # Perfil y contraseña
    path("profile/", views.profile_view, name="profile"),
    path("password-change/", views.password_change_custom, name="password_change_custom"),

    # Auth
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset_view, name="password_reset"),

    # Página sin organización
    path("no-org/", views.no_org_view, name="no_org"),
]
