# core/views.py

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.utils import timezone

from django.contrib.auth.models import User
from .models import Account, Device, Category

from .models import (
    Organization,
    Category,
    Zone,
    Device,
    Measurement,
    Alert,
    Account,
)


# ============================
# Helpers de organización / roles
# ============================

def _user_org_or_none(user):
    """
    Devuelve la organización del usuario (si tiene Account).
    - Superuser puede no tener organización => retorna None.
    """
    if user.is_superuser:
        # Para superuser intentamos usar la organización del Account si existe
        acc = getattr(user, "account", None)
        if acc and acc.organization_id:
            return acc.organization
        return None

    acc = getattr(user, "account", None)
    return acc.organization if acc and acc.organization_id else None


def _require_org_or_redirect(request):
    """
    Devuelve True si el usuario puede trabajar con datos de organización.
    - Superuser: siempre True (aunque no tenga organization).
    - Otros: deben tener Account y organization.
    """
    if request.user.is_superuser:
        return True

    acc = getattr(request.user, "account", None)
    return bool(acc and acc.organization_id)


def no_org_view(request):
    """
    Vista simple cuando el usuario no tiene organización asociada.
    """
    return render(request, "core/no_org.html")


def is_org_admin(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.ORG_ADMIN)


def is_verifier(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.VERIFIER)


def is_member(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.MEMBER)


def _can_manage_devices(user):
    """
    Devuelve True si el usuario puede crear/editar/eliminar dispositivos.
    - superuser: siempre True
    - ORG_ADMIN y VERIFIER: True
    - MEMBER: False
    """
    if user.is_superuser:
        return True

    acc = getattr(user, "account", None)
    if not acc:
        return False

    return acc.role in (Account.Role.ORG_ADMIN, Account.Role.VERIFIER)


# =============================
# Dashboard
# =============================

@login_required
def dashboard(request):
    if not _require_org_or_redirect(request):
        return redirect("no_org")

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

    devices_by_category = {
        c.name: devices_qs.filter(category=c).count()
        for c in categories
    }
    devices_by_zone = {
        z.name: devices_qs.filter(zone=z).count()
        for z in zones
    }

    # Últimas mediciones (filtrando ANTES de cortar)
    latest_measurements_qs = Measurement.objects.select_related("device").order_by("-created_at")
    if org:
        latest_measurements_qs = latest_measurements_qs.filter(device__organization=org)
    latest_measurements = latest_measurements_qs[:10]

    # Alertas recientes
    recent_alerts_qs = Alert.objects.select_related("device").order_by("-created_at")
    if org:
        recent_alerts_qs = recent_alerts_qs.filter(device__organization=org)
    recent_alerts = recent_alerts_qs[:5]

    # Contadores semanales por prioridad
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    weekly_alerts_qs = Alert.objects.filter(created_at__gte=week_ago)
    if org:
        weekly_alerts_qs = weekly_alerts_qs.filter(device__organization=org)

    grave_count = weekly_alerts_qs.filter(priority="grave").count()
    alto_count = weekly_alerts_qs.filter(priority="alto").count()
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


# =============================
# Listados de Measurement / Alert
# =============================

@login_required
def measurement_list(request):
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    org = _user_org_or_none(request.user)
    measurements = Measurement.objects.select_related("device").order_by("-created_at")
    if org:
        measurements = measurements.filter(device__organization=org)
    return render(request, "core/measurement_list.html", {"measurements": measurements})


@login_required
def alert_list(request):
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    org = _user_org_or_none(request.user)
    alerts = Alert.objects.select_related("device").order_by("-created_at")
    if org:
        alerts = alerts.filter(device__organization=org)
    return render(request, "core/alert_list.html", {"alerts": alerts})


@login_required
def alerts_week(request):
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    org = _user_org_or_none(request.user)
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    alerts = Alert.objects.filter(created_at__gte=week_ago).order_by("-created_at")
    if org:
        alerts = alerts.filter(device__organization=org)
    return render(request, "core/alerts_week.html", {"alerts": alerts})


# =============================
# Auth: login / logout / register / reset
# =============================

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


def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=email).exists():
            messages.error(request, "Ya existe un usuario con este correo.")
        else:
            # Solo crea el usuario. El Account lo crea el signal post_save(User).
            User.objects.create_user(username=email, email=email, password=password)
            messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect("login")

    return render(request, "core/register.html")


def password_reset_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        messages.success(request, f"Se enviaron instrucciones de recuperación al correo {email} (simulado).")
        return redirect("login")

    return render(request, "core/password_reset.html")
@login_required
def profile_view(request):
    """
    Permite editar:
    - nombre (usaremos user.username)
    - correo
    - teléfono (Account.phone)
    - avatar (Account.avatar)
    """
    user = request.user
    acc = getattr(user, "account", None)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            phone = form.cleaned_data["phone"]
            avatar = form.cleaned_data.get("avatar")

            user.username = name
            user.email = email
            user.save()

            if acc:
                acc.phone = phone
                if avatar:
                    acc.avatar = avatar
                acc.save()

            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("profile")
    else:
        initial = {
            "name": user.username,
            "email": user.email,
            "phone": getattr(acc, "phone", "") if acc else "",
        }
        form = ProfileForm(initial=initial)

    return render(request, "core/profile.html", {
        "form": form,
        "account": acc,
    })


@login_required
def password_change_custom(request):
    """
    Cambio de contraseña con validaciones personalizadas.
    """
    if request.method == "POST":
        form = PasswordChangeCustomForm(request.POST)
        if form.is_valid():
            current = form.cleaned_data["current_password"]
            new = form.cleaned_data["new_password"]

            if not request.user.check_password(current):
                form.add_error("current_password", "La contraseña actual no es correcta.")
            else:
                request.user.set_password(new)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Contraseña cambiada correctamente.")
                return redirect("profile")
    else:
        form = PasswordChangeCustomForm()

    return render(request, "core/password_change.html", {"form": form})
