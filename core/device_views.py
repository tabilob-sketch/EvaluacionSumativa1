# core/device_views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect

from .models import Device, Measurement, Alert, Category, Zone, Organization
from .forms import DeviceForm
from .views import _require_org_or_redirect, _user_org_or_none, _can_manage_devices


@login_required
def device_list(request):
    """
    Lista de dispositivos, filtrados por organización y por
    categoría/zona si se envían por GET.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    org = _user_org_or_none(request.user)

    devices = Device.objects.select_related("category", "zone", "organization").all()
    categories = Category.objects.all()
    zones = Zone.objects.all()

    # Si el usuario tiene organización (no-superuser), filtramos por ella.
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
        # usamos esto en el template para mostrar/ocultar botón Crear
        "can_manage_devices": _can_manage_devices(request.user),
    }
    return render(request, "core/device_list.html", context)


@login_required
def device_detail(request, device_id):
    """
    Detalle de un dispositivo. Respeta la organización del usuario.
    """
    org = _user_org_or_none(request.user)
    base = Device.objects.select_related("category", "zone", "organization")
    if org and not request.user.is_superuser:
        base = base.filter(organization=org)

    device = get_object_or_404(base, id=device_id)

    measurements = Measurement.objects.filter(device=device).order_by("-created_at")[:20]
    alerts = Alert.objects.filter(device=device).order_by("-created_at")[:10]

    context = {
        "device": device,
        "measurements": measurements,
        "alerts": alerts,
        "can_manage_devices": _can_manage_devices(request.user),
    }
    return render(request, "core/device_detail.html", context)


@login_required
def device_create(request):
    """
    Crea un nuevo Device dentro de la organización del usuario.
    Solo para usuarios con permiso (_can_manage_devices).
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request.user):
        return HttpResponseForbidden("No tienes permiso para crear dispositivos.")

    org = _user_org_or_none(request.user)

    # Si el usuario es superuser y no tiene org en Account,
    # usamos la primera organización disponible en la BD.
    if org is None and request.user.is_superuser:
        org = Organization.objects.order_by("id").first()

    # Si aún no hay organización, no podemos crear el dispositivo.
    if org is None:
        messages.error(request, "No hay organización disponible para asociar el dispositivo.")
        return redirect("device_list")

    if request.method == "POST":
        form = DeviceForm(request.POST)

        # Limitamos categorías y zonas a la organización del usuario
        form.fields["category"].queryset = Category.objects.filter(organization=org)
        form.fields["zone"].queryset = Zone.objects.filter(organization=org)

        if form.is_valid():
            device = form.save(commit=False)
            # SIEMPRE seteamos organization (clave del error que tenías)
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
    Solo para usuarios con permiso (_can_manage_devices).
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request.user):
        return HttpResponseForbidden("No tienes permiso para editar dispositivos.")

    org = _user_org_or_none(request.user)

    # Superuser puede ver todos, los demás solo su org
    base = Device.objects.select_related("category", "zone", "organization")
    if org and not request.user.is_superuser:
        base = base.filter(organization=org)

    device = get_object_or_404(base, id=device_id)

    if request.method == "POST":
        form = DeviceForm(request.POST, instance=device)
        if org:
            form.fields["category"].queryset = Category.objects.filter(organization=org)
            form.fields["zone"].queryset = Zone.objects.filter(organization=org)

        if form.is_valid():
            device = form.save(commit=False)
            # Para usuarios normales, fijamos la org de su cuenta
            if org and not request.user.is_superuser:
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
    Solo para usuarios con permiso (_can_manage_devices).
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request.user):
        return HttpResponseForbidden("No tienes permiso para eliminar dispositivos.")

    org = _user_org_or_none(request.user)
    base = Device.objects.select_related("organization")
    if org and not request.user.is_superuser:
        base = base.filter(organization=org)

    device = get_object_or_404(base, id=device_id)

    if request.method == "POST":
        device.delete()
        messages.success(request, "Dispositivo eliminado correctamente.")
        return redirect("device_list")

    return render(request, "core/device_confirm_delete.html", {
        "device": device,
    })
