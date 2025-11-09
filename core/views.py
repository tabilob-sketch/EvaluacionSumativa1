from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Account

from django.utils import timezone
from datetime import timedelta

from .models import (
    Device, Measurement, Alert, Category, Zone,
    Organization,
    Account,
)
from .forms import DeviceForm ,CategoryForm

# ============================
# Helpers de organización / roles (para vistas)
# ============================

def _user_org_or_none(user):
    if user.is_superuser:
        return None
    acc = getattr(user, "account", None)
    return acc.organization if acc else None


def is_org_admin(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.ORG_ADMIN)


def is_verifier(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.VERIFIER)


def is_member(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.MEMBER)


def _require_org_or_redirect(request):
    """
    Devuelve True si el usuario puede trabajar con datos de organización.
    - Superuser: siempre True.
    - Otros: deben tener Account y organization.
    """
    if request.user.is_superuser:
        return True
    acc = getattr(request.user, "account", None)
    return bool(acc and acc.organization_id)


def no_org_view(request):
    return render(request, "core/no_org.html")


# =============================
# Helpers de organización/rol
# =============================

def _require_org_or_redirect(request):
    # Superuser puede acceder siempre, aunque no tenga organization
    if request.user.is_superuser:
        return True
    return hasattr(request.user, "account") and request.user.account.organization is not None


def no_org_view(request):
    return render(request, "core/no_org.html")


def _user_org_or_none(user):
    if user.is_superuser:
        return None
    acc = getattr(user, "account", None)
    return acc.organization if acc else None


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

    devices_by_category = {c.name: devices_qs.filter(category=c).count() for c in categories}
    devices_by_zone = {z.name: devices_qs.filter(zone=z).count() for z in zones}

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
# CRUD de Device
# =============================

@login_required
@login_required
def device_list(request):

    if not _require_org_or_redirect(request):
        return redirect("no_org")
    
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
        "can_manage_devices": _can_manage_devices(request.user),  
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
        "can_manage_devices": _can_manage_devices(request.user),  # <- NUEVO
    }
    return render(request, "core/device_detail.html", context)



@login_required
def device_create(request):
    """
    Crea un nuevo Device dentro de la organización del usuario.
    - Usa DeviceForm.
    - Asigna organization automáticamente según el usuario.
    """
    # 1) Sacamos la organización del usuario desde Account
    acc = getattr(request.user, "account", None)
    org = acc.organization if acc and acc.organization_id else None

    # 2) Si no tiene organización, mostramos error amable y NO guardamos nada
    if org is None:
        messages.error(request, "No tienes una organización asociada. Pide al administrador que te asigne una.")
        return redirect("device_list")

    if request.method == "POST":
        form = DeviceForm(request.POST)

        # 3) Limitamos las opciones a la organización del usuario
        form.fields["category"].queryset = Category.objects.filter(organization=org)
        form.fields["zone"].queryset = Zone.objects.filter(organization=org)

        if form.is_valid():
            # 4) Creamos el Device pero todavía no grabamos
            device = form.save(commit=False)
            # 5) Seteamos SIEMPRE la organización antes de hacer save()
            device.organization = org
            device.save()
            messages.success(request, "Dispositivo creado correctamente.")
            return redirect("device_list")
    else:
        form = DeviceForm()
        form.fields["category"].queryset = Category.objects.filter(organization=org)
        form.fields["zone"].queryset = Zone.objects.filter(organization=org)

    return render(request, "core/device_form.html", {
        "form": form,
        "mode": "create",
    })




@login_required
def device_update(request, device_id):
    """
    Edita un Device que pertenece a la organización del usuario.
    Solo superuser y ORG_ADMIN pueden editar.
    """
    if not _require_org_or_redirect(request):
        return render(request, "core/no_org.html", {
            "mensaje": "Tu usuario no tiene una organización asociada. Contacta al administrador."
        })

    # Solo superuser u ORG_ADMIN
    if not (request.user.is_superuser or is_org_admin(request.user)):
        messages.error(request, "No tienes permisos para editar dispositivos.")
        return redirect("device_detail", device_id=device_id)

    org = _user_org_or_none(request.user)

    base = Device.objects.select_related("category", "zone", "organization")
    if org:
        base = base.filter(organization=org)
    device = get_object_or_404(base, id=device_id)

    if request.method == "POST":
        form = DeviceForm(request.POST, instance=device)
        if org:
            form.fields["category"].queryset = Category.objects.filter(organization=org)
            form.fields["zone"].queryset = Zone.objects.filter(organization=org)

        if form.is_valid():
            device = form.save(commit=False)
            if org:
                device.organization = org
            device.save()
            messages.success(request, "Dispositivo actualizado correctamente.")
            return redirect("device_detail", device_id=device.id)
    else:
        form = DeviceForm(instance=device)
        if org:
            form.fields["category"].queryset = Category.objects.filter(organization=org)
            form.fields["zone"].queryset = Zone.objects.filter(organization=org)

    return render(request, "core/device_form.html", {
        "form": form,
        "mode": "edit",
        "device": device,
    })



@login_required
def device_delete(request, device_id):
    """
    Elimina un Device de la organización del usuario.
    Solo superuser y ORG_ADMIN pueden eliminar.
    """
    if not _require_org_or_redirect(request):
        return render(request, "core/no_org.html", {
            "mensaje": "Tu usuario no tiene una organización asociada. Contacta al administrador."
        })
    
    #categorias

    @login_required
    def category_list(request):
        """
        Listado de categorías de la organización del usuario.
        ORG_ADMIN / VERIFIER / MEMBER pueden ver.
        """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    org = _user_org_or_none(request.user)

    categories = Category.objects.all()
    if org:
        categories = categories.filter(organization=org)

    context = {
        "categories": categories,
    }
    return render(request, "core/category_list.html", context)


@login_required
def category_create(request):
    """
    Crea una nueva Category dentro de la organización del usuario.
    Solo ORG_ADMIN y VERIFIER.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request):
        messages.error(request, "No tienes permiso para crear categorías.")
        return redirect("category_list")

    org = _user_org_or_none(request.user)
    if org is None:
        messages.error(request, "No tienes una organización asociada.")
        return redirect("dashboard")

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.organization = org
            category.save()
            messages.success(request, "Categoría creada correctamente.")
            return redirect("category_list")
    else:
        form = CategoryForm()

    return render(request, "core/category_form.html", {
        "form": form,
        "mode": "create",
    })


@login_required
def category_update(request, category_id):
    """
    Edita una Category dentro de la organización del usuario.
    Solo ORG_ADMIN y VERIFIER.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request):
        messages.error(request, "No tienes permiso para editar categorías.")
        return redirect("category_list")

    org = _user_org_or_none(request.user)

    qs = Category.objects.all()
    if org:
        qs = qs.filter(organization=org)

    category = get_object_or_404(qs, id=category_id)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()  # organization ya está fijada
            messages.success(request, "Categoría actualizada correctamente.")
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)

    return render(request, "core/category_form.html", {
        "form": form,
        "mode": "edit",
        "category": category,
    })


@login_required
def category_delete(request, category_id):
    """
    Elimina una Category dentro de la organización del usuario.
    Solo ORG_ADMIN y VERIFIER.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request):
        messages.error(request, "No tienes permiso para eliminar categorías.")
        return redirect("category_list")

    org = _user_org_or_none(request.user)

    qs = Category.objects.all()
    if org:
        qs = qs.filter(organization=org)

    category = get_object_or_404(qs, id=category_id)

    if request.method == "POST":
        category.delete()
        messages.success(request, "Categoría eliminada correctamente.")
        return redirect("category_list")

    return render(request, "core/category_confirm_delete.html", {
        "category": category,
    })

    # Solo superuser u ORG_ADMIN
    if not (request.user.is_superuser or is_org_admin(request.user)):
        messages.error(request, "No tienes permisos para eliminar dispositivos.")
        return redirect("device_detail", device_id=device_id)

    org = _user_org_or_none(request.user)
    base = Device.objects.select_related("organization")
    if org:
        base = base.filter(organization=org)

    device = get_object_or_404(base, id=device_id)

    if request.method == "POST":
        device.delete()
        messages.success(request, "Dispositivo eliminado correctamente.")
        return redirect("device_list")

    return render(request, "core/device_confirm_delete.html", {
        "device": device,
    })



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
            user = User.objects.create_user(username=email, email=email, password=password)

            messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect("login")

    return render(request, "core/register.html")


def password_reset_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        messages.success(request, f"Se enviaron instrucciones de recuperación al correo {email} (simulado).")
        return redirect("login")

    return render(request, "core/password_reset.html")
