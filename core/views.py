from django.shortcuts import render
from .models import Device, Measurement, Alert, Category, Zone


def dashboard(request):
    categories = Category.objects.all()
    zones = Zone.objects.all()

    devices_by_category = {c.name: Device.objects.filter(category=c).count() for c in categories}
    devices_by_zone = {z.name: Device.objects.filter(zone=z).count() for z in zones}

    latest_measurements = Measurement.objects.order_by("-created_at")[:10]
    recent_alerts = Alert.objects.order_by("-created_at")[:5]

    # filtros
    category_id = request.GET.get("category")
    zone_id = request.GET.get("zone")

    devices = Device.objects.all()
    if category_id and category_id != "all":
        devices = devices.filter(category_id=category_id)
    if zone_id and zone_id != "all":
        devices = devices.filter(zone_id=zone_id)

    context = {
        "devices_by_category": devices_by_category,
        "devices_by_zone": devices_by_zone,
        "latest_measurements": latest_measurements,
        "recent_alerts": recent_alerts,
        "categories": categories,
        "zones": zones,
        "devices": devices,
    }
    return render(request, "core/dashboard.html", context)


def device_list(request):
    category_id = request.GET.get("category", "all")
    zone_id = request.GET.get("zone", "all")

    devices = Device.objects.all()
    categories = Category.objects.all()
    zones = Zone.objects.all()

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

def device_detail(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    measurements = Measurement.objects.filter(device=device).order_by("-created_at")[:20]
    alerts = Alert.objects.filter(device=device).order_by("-created_at")[:10]

    context = {
        "device": device,
        "measurements": measurements,
        "alerts": alerts,
    }
    return render(request, "core/device_detail.html", context)    
def measurement_list(request):
    measurements = Measurement.objects.select_related("device").order_by("-created_at")
    return render(request, "core/measurement_list.html", {"measurements": measurements})
def alert_list(request):
    alerts = Alert.objects.select_related("device").order_by("-created_at")
    return render(request, "core/alert_list.html", {"alerts": alerts})
def login_view(request):
    return render(request, 'core/login.html')

def register_view(request):
    return render(request, 'core/register.html')
