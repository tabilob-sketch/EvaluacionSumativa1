# core/device_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.core.paginator import Paginator

import csv

from .models import Device, Measurement, Alert, Category, Zone
from .views import _require_org_or_redirect, _user_org_or_none, _can_manage_devices


@login_required
def device_list(request):
    """
    Listado de dispositivos con:
    - Filtros por categoría y zona
    - Paginación
    - Exportación a CSV (Excel compatible)
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

    # Filtros (recordados en sesión)
    category_id = request.GET.get("category", request.session.get("filter_category", "all"))
    zone_id = request.GET.get("zone", request.session.get("filter_zone", "all"))

    request.session["filter_category"] = category_id
    request.session["filter_zone"] = zone_id

    if category_id != "all":
        devices = devices.filter(category_id=category_id)
    if zone_id != "all":
        devices = devices.filter(zone_id=zone_id)

    # Exportar a "Excel" (CSV)
    if request.GET.get("export") == "excel":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="dispositivos.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Nombre", "Categoría", "Zona", "Organización", "Estado"])

        for d in devices:
            writer.writerow([
                d.id,
                d.name,
                getattr(d.category, "name", ""),
                getattr(d.zone, "name", ""),
                getattr(d.organization, "name", ""),
                getattr(d, "status", ""),
            ])

        return response

    # Paginación
    paginator = Paginator(devices, 9)  # 9 por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "devices": page_obj.object_list,
        "page_obj": page_obj,
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
    if org is None and not request.user.is_superuser:
        messages.error(request, "No tienes una organización asociada.")
        return redirect("dashboard")

    from .forms import DeviceForm  # import local para evitar ciclos

    if request.method == "POST":
        form = DeviceForm(request.POST)
        if org:
            form.fields["category"].queryset = Category.objects.filter(organization=org)
            form.fields["zone"].queryset = Zone.objects.filter(organization=org)

        if form.is_valid():
            device = form.save(commit=False)
            if not request.user.is_superuser:
                device.organization = org
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

    from .forms import DeviceForm

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
