from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.utils import timezone
from datetime import timedelta

from .models import (
    Device, Measurement, Alert, Category, Zone,
    Organization,  
    Account,       
)


# Helper: obtener la Organization del usuario (si no es superuser)

def _user_org_or_none(user):
    if user.is_superuser:
        return None
    acc = getattr(user, "account", None)
    return acc.organization if acc else None



# VISTAS PROTEGIDAS

@login_required
def dashboard(request):
    org = _user_org_or_none(request.user)  

    categories = Category.objects.all()
    zones = Zone.objects.all()
    if org:
        categories = categories.filter(organization=org)
        zones = zones.filter(organization=org)

    # Devices base filtrados por org
    devices_qs = Device.objects.select_related("category", "zone", "organization")
    if org:
        devices_qs = devices_qs.filter(organization=org)

    devices_by_category = {c.name: devices_qs.filter(category=c).count() for c in categories}
    devices_by_zone = {z.name: devices_qs.filter(zone=z).count() for z in zones}

    # Construye el queryset, filtra (si aplica) y recién ahí corta
    latest_measurements_qs = Measurement.objects.select_related("device").order_by("-created_at")
    if org:
        latest_measurements_qs = latest_measurements_qs.filter(device__organization=org)
    latest_measurements = latest_measurements_qs[:10]

    recent_alerts_qs = Alert.objects.select_related("device").order_by("-created_at")
    if org:
        recent_alerts_qs = recent_alerts_qs.filter(device__organization=org)
    recent_alerts = recent_alerts_qs[:5]

    # Contadores semanales por prioridad (filtra antes)
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    weekly_alerts_qs = Alert.objects.filter(created_at__gte=week_ago)
    if org:
        weekly_alerts_qs = weekly_alerts_qs.filter(device__organization=org)

    grave_count = weekly_alerts_qs.filter(priority="grave").count()
    alto_count  = weekly_alerts_qs.filter(priority="alto").count()
    medio_count = weekly_alerts_qs.filter(priority="medio").count()

    # Filtros del grid de dispositivos del dashboard
    category_id = request.GET.get("category")
    zone_id = request.GET.get("zone")

    devices = devices_qs
    if category_id and category_id != "all":
        devices = devices.filter(category_id=category_id)
    if zone_id and zone_id != "all":
        devices = devices.filter(zone_id=zone_id)

    context = {
        "devices_by_category": devices_by_category,
        "devices_by_zone": devices_by_zone,
        "latest_measurements": latest_measurements,
        "recent_alerts": recent_alerts,
        "grave_count": grave_count,
        "alto_count": alto_count,
        "medio_count": medio_count,
        "categories": categories,
        "zones": zones,
        "devices": devices,
    }
    return render(request, "core/dashboard.html", context)



@login_required
def device_list(request):
    org = _user_org_or_none(request.user)

    devices = Device.objects.select_related("category", "zone", "organization").all()
    categories = Category.objects.all()
    zones = Zone.objects.all()

    if org:
        devices = devices.filter(organization=org)
        categories = categories.filter(organization=org)
        zones = zones.filter(organization=org)

    category_id = request.GET.get("category", "all")
    zone_id = request.GET.get("zone", "all")

    if category_id != "all":
        devices = devices.filter(category_id=category_id)
    if zone_id != "all":
        devices = devices.filter(zone_id=zone_id)

    context = {
        "devices": devices,
        "categories": categories,
        "zones": zones,
        "selected_category": category_id,
        "selected_zone": zone_id,
    }
    return render(request, "core/device_list.html", context)


@login_required
def device_detail(request, device_id):
    org = _user_org_or_none(request.user)
    base = Device.objects.select_related("category", "zone", "organization")
    if org:
        base = base.filter(organization=org)
    device = get_object_or_404(base, id=device_id)

    measurements = Measurement.objects.filter(device=device).order_by("-created_at")[:20]
    alerts = Alert.objects.filter(device=device).order_by("-created_at")[:10]

    context = {
        "device": device,
        "measurements": measurements,
        "alerts": alerts,
    }
    return render(request, "core/device_detail.html", context)


@login_required
def measurement_list(request):
    org = _user_org_or_none(request.user)
    measurements = Measurement.objects.select_related("device").order_by("-created_at")
    if org:
        measurements = measurements.filter(device__organization=org)
    return render(request, "core/measurement_list.html", {"measurements": measurements})


@login_required
def alert_list(request):
    org = _user_org_or_none(request.user)
    alerts = Alert.objects.select_related("device").order_by("-created_at")
    if org:
        alerts = alerts.filter(device__organization=org)
    return render(request, "core/alert_list.html", {"alerts": alerts})


@login_required
def alerts_week(request):
    org = _user_org_or_none(request.user)
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    alerts = Alert.objects.filter(created_at__gte=week_ago).order_by("-created_at")
    if org:
        alerts = alerts.filter(device__organization=org)
    return render(request, "core/alerts_week.html", {"alerts": alerts})



# AUTH: Login / Logout / Register

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Credenciales inválidas, intenta de nuevo.")

    return render(request, "core/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


from .models import Organization, Account

def register_view(request):
    if request.method == "POST":
        company_name = request.POST.get("company_name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not company_name:
            messages.error(request, "Debes indicar el nombre de tu empresa.")
            return render(request, "core/register.html")

        if User.objects.filter(username=email).exists():
            messages.error(request, "Ya existe un usuario con este correo.")
        else:
            org, _ = Organization.objects.get_or_create(name=company_name.strip())
            user = User.objects.create_user(username=email, email=email, password=password)

            # vincula la org al Account del usuario
            account = getattr(user, "account", None)
            if account is None:
                account = Account.objects.create(user=user, organization=org)
            else:
                account.organization = org
                account.save()

            messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect("login")

    return render(request, "core/register.html")


def password_reset_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        messages.success(request, f"Se enviaron instrucciones de recuperación al correo {email} (simulado).")
        return redirect("login")

    return render(request, "core/password_reset.html")


