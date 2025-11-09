# core/device_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Device, Measurement, Alert, Category, Zone
from .forms import DeviceForm

# Importamos helpers que ya definiste en views.py
from .views import _require_org_or_redirect, _user_org_or_none, _can_manage_devices


@login_required
def device_list(request):
    """
    Lista de dispositivos, filtrados por organización del usuario.
    Admin ve botón de crear, lector solo ve la lista.
    """
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
    """
    Detalle de un dispositivo.
    Admin verá botones de editar/eliminar, lector no.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

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
        "can_manage_devices": _can_manage_devices(request.user),
    }
    return render(request, "core/device_detail.html", context)


@login_required
def device_create(request):
    """
    Crea un nuevo Device.
    - Solo admin puede crear.
    - Se asigna automáticamente la organización según el usuario.
      Si es superuser, se usa la organización de la categoría elegida.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request.user):
        messages.error(request, "No tienes permiso para crear dispositivos.")
        return redirect("device_list")

    org = _user_org_or_none(request.user)

    if request.method == "POST":
        form = DeviceForm(request.POST)

        # Opciones de category/zone según organización
        if org:
            form.fields["category"].queryset = Category.objects.filter(organization=org)
            form.fields["zone"].queryset = Zone.objects.filter(organization=org)
        else:
            form.fields["category"].queryset = Category.objects.all()
            form.fields["zone"].queryset = Zone.objects.all()

        if form.is_valid():
            device = form.save(commit=False)

            if org:
                # Usuario normal: organización fija
                device.organization = org
            else:
                # Superuser: inferimos la org desde la categoría
                if device.category and device.category.organization_id:
                    device.organization_id = device.category.organization_id
                else:
                    messages.error(request, "No se pudo determinar la organización del dispositivo.")
                    return render(request, "core/device_form.html", {
                        "form": form,
                        "mode": "create",
                    })

            device.save()
            messages.success(request, "Dispositivo creado correctamente.")
            return redirect("device_list")
    else:
        form = DeviceForm()
        if org:
            form.fields["category"].queryset = Category.objects.filter(organization=org)
            form.fields["zone"].queryset = Zone.objects.filter(organization=org)
        else:
            form.fields["category"].queryset = Category.objects.all()
            form.fields["zone"].queryset = Zone.objects.all()

    return render(request, "core/device_form.html", {
        "form": form,
        "mode": "create",
    })


@login_required
def device_update(request, device_id):
    """
    Edita un Device.
    Solo admin puede editar.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request.user):
        messages.error(request, "No tienes permiso para editar dispositivos.")
        return redirect("device_list")

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
        else:
            form.fields["category"].queryset = Category.objects.all()
            form.fields["zone"].queryset = Zone.objects.all()

        if form.is_valid():
            device = form.save(commit=False)

            if org:
                device.organization = org
            else:
                # superuser: organización igual a la de la categoría
                if device.category and device.category.organization_id:
                    device.organization_id = device.category.organization_id
                else:
                    messages.error(request, "No se pudo determinar la organización del dispositivo.")
                    return render(request, "core/device_form.html", {
                        "form": form,
                        "mode": "edit",
                        "device": device,
                    })

            device.save()
            messages.success(request, "Dispositivo actualizado correctamente.")
            return redirect("device_detail", device_id=device.id)
    else:
        form = DeviceForm(instance=device)

        if org:
            form.fields["category"].queryset = Category.objects.filter(organization=org)
            form.fields["zone"].queryset = Zone.objects.filter(organization=org)
        else:
            form.fields["category"].queryset = Category.objects.all()
            form.fields["zone"].queryset = Zone.objects.all()

    return render(request, "core/device_form.html", {
        "form": form,
        "mode": "edit",
        "device": device,
    })


@login_required
def device_delete(request, device_id):
    """
    Elimina un Device.
    Solo admin puede eliminar.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request.user):
        messages.error(request, "No tienes permiso para eliminar dispositivos.")
        return redirect("device_list")

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
