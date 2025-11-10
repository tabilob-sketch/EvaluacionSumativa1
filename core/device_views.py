# core/device_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator

from .models import Device, Measurement, Alert, Category, Zone, Organization
from .forms import DeviceForm
from .views import _require_org_or_redirect, _user_org_or_none, _can_manage_devices


@login_required
def device_list(request):
    """
    Lista de dispositivos con filtros por categoría y zona + paginación.
    Respeta la organización del usuario.
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    org = _user_org_or_none(request.user)

    devices_qs = Device.objects.select_related("category", "zone", "organization").all()
    categories = Category.objects.all()
    zones = Zone.objects.all()

    if org:
        devices_qs = devices_qs.filter(organization=org)
        categories = categories.filter(organization=org)
        zones = zones.filter(organization=org)

    # filtros
    category_id = request.GET.get("category", "all")
    zone_id = request.GET.get("zone", "all")

    if category_id != "all":
        devices_qs = devices_qs.filter(category_id=category_id)
    if zone_id != "all":
        devices_qs = devices_qs.filter(zone_id=zone_id)

    # paginación (6 dispositivos por página)
    page_number = request.GET.get("page", 1)
    paginator = Paginator(devices_qs, 6)
    page_obj = paginator.get_page(page_number)

    context = {
        "devices": page_obj,              # para compatibilidad si usas "devices"
        "page_obj": page_obj,            # objeto de paginación
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
    Detalle de un dispositivo, últimas mediciones y alertas.
    """
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
    Crea un nuevo Device dentro de la organización del usuario.
    Solo para usuarios con permiso (_can_manage_devices).

    - Usuarios normales: se usa Account.organization.
    - Superuser: si no tiene organización asociada, se usa la primera Organization
      disponible como fallback (para pruebas).
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request.user):
        return HttpResponseForbidden("No tienes permiso para crear dispositivos.")

    org = _user_org_or_none(request.user)  # puede ser None si es superuser sin org

    # Si no hay ninguna organización en BD, no podemos crear nada
    if not org and not request.user.is_superuser:
        messages.error(request, "No tienes una organización asociada.")
        return redirect("dashboard")

    if request.method == "POST":
        form = DeviceForm(request.POST)

        # Limitamos category/zone a la organización del usuario (si tiene)
        if org:
            form.fields["category"].queryset = Category.objects.filter(organization=org)
            form.fields["zone"].queryset = Zone.objects.filter(organization=org)

        if form.is_valid():
            device = form.save(commit=False)

            if org:
                # Usuario con organización normal
                device.organization = org
            else:
                # Superuser sin org: intentamos usar la primera Organización como fallback
                fallback_org = Organization.objects.first()
                if fallback_org:
                    device.organization = fallback_org

            # Si aún no hay organización, no guardamos para evitar IntegrityError
            if device.organization is None:
                messages.error(
                    request,
                    "No se pudo determinar una organización para el dispositivo. "
                    "Crea una organización primero en el panel de administración."
                )
                return redirect("device_list")

            device.save()
            messages.success(request, "Dispositivo creado correctamente.")
            return redirect("device_list")
    else:
        form = DeviceForm()
        if org:
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


@login_required
def device_export(request):
    """
    Exporta a CSV (Excel compatible) el listado de dispositivos filtrado
    por categoría y zona, y respetando la organización del usuario.
    Solo para usuarios con permiso (_can_manage_devices).
    """
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    if not _can_manage_devices(request.user):
        return HttpResponseForbidden("No tienes permiso para exportar dispositivos.")

    org = _user_org_or_none(request.user)

    qs = Device.objects.select_related("category", "zone", "organization").all()
    if org and not request.user.is_superuser:
        qs = qs.filter(organization=org)

    # Aplicar mismos filtros que en device_list
    category_id = request.GET.get("category", "all")
    zone_id = request.GET.get("zone", "all")

    if category_id != "all":
        qs = qs.filter(category_id=category_id)
    if zone_id != "all":
        qs = qs.filter(zone_id=zone_id)

    import csv

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="dispositivos.csv"'

    writer = csv.writer(response)
    # Encabezados
    writer.writerow([
        "ID",
        "Nombre",
        "Organización",
        "Categoría",
        "Zona",
    ])

    # Filas
    for d in qs:
        writer.writerow([
            d.id,
            d.name,
            d.organization.name if d.organization else "",
            d.category.name if d.category else "",
            d.zone.name if d.zone else "",
        ])

    return response
