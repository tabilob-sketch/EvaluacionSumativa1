# core/device_views.py

import csv
from django.utils.encoding import smart_str

from django.db import IntegrityError
from django.core.exceptions import ValidationError

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
    if not _require_org_or_redirect(request):
        return redirect("no_org")

    org = _user_org_or_none(request.user)

    if request.method == "POST":
        name = request.POST.get("name")
        category_id = request.POST.get("category")
        zone_id = request.POST.get("zone")

        if not name or not category_id or not zone_id:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect("device_create")

        try:
            category = Category.objects.get(id=category_id, organization=org)
            zone = Zone.objects.get(id=zone_id, organization=org)

            device = Device(
                name=name,
                category=category,
                zone=zone,
                organization=org  # ⬅⬅⬅ ESTO ES LO QUE FALTABA
            )

            device.full_clean()  # valida el modelo
            device.save()

            messages.success(request, "Dispositivo creado correctamente.")
            return redirect("device_list")

        except Category.DoesNotExist:
            messages.error(request, "La categoría seleccionada no existe.")
        except Zone.DoesNotExist:
            messages.error(request, "La zona seleccionada no existe.")
        except IntegrityError:
            messages.error(request, "Ya existe un dispositivo con este nombre.")
        except ValidationError as e:
            messages.error(request, f"Error de validación: {e}")
        except Exception as e:
            messages.error(request, f"Error inesperado: {e}")

        return redirect("device_create")

    categories = Category.objects.filter(organization=org)
    zones = Zone.objects.filter(organization=org)

    return render(request, "core/device_create.html", {
        "categories": categories,
        "zones": zones
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

    # Ordenar para que quede ordenado en Excel
    qs = qs.order_by("organization__name", "category__name", "zone__name", "name")

    # CSV pensado para Excel en español: ; como separador + BOM UTF-8
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="dispositivos.csv"'

    writer = csv.writer(response, delimiter=';', quoting=csv.QUOTE_MINIMAL)

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
            smart_str(d.name),
            smart_str(d.organization.name if d.organization else ""),
            smart_str(d.category.name if d.category else ""),
            smart_str(d.zone.name if d.zone else ""),
        ])

    return response

