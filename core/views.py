from django.shortcuts import render, get_object_or_404
from .models import Device, Measurement, Alert, Category, Zone
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User





def dashboard(request):
    categories = Category.objects.all()
    zones = Zone.objects.all()

    devices_by_category = {c.name: Device.objects.filter(category=c).count() for c in categories}
    devices_by_zone = {z.name: Device.objects.filter(zone=z).count() for z in zones}

    latest_measurements = Measurement.objects.order_by("-created_at")[:10]
    recent_alerts = Alert.objects.order_by("-created_at")[:5]

    # ✅ Contar alertas de la semana por prioridad
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    weekly_alerts = Alert.objects.filter(created_at__gte=week_ago)

    grave_count = weekly_alerts.filter(priority="grave").count()
    alto_count = weekly_alerts.filter(priority="alto").count()
    medio_count = weekly_alerts.filter(priority="medio").count()

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
        "grave_count": grave_count,   # ✅
        "alto_count": alto_count,     # ✅
        "medio_count": medio_count,   # ✅
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
def alerts_week(request):
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    alerts = Alert.objects.filter(created_at__gte=week_ago).order_by("-created_at")

    return render(request, "core/alerts_week.html", {"alerts": alerts})

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Autenticación
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")  
        else:
            messages.error(request, "Credenciales inválidas, intenta de nuevo.")

    return render(request, "core/login.html")

def register_view(request):
    if request.method == "POST":
        company_name = request.POST.get("company_name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=email).exists():
            messages.error(request, "Ya existe un usuario con este correo.")
        else:
            # Crear la empresa
            from .models import Organization
            org = Organization.objects.create(name=company_name)

            # Crear usuario
            user = User.objects.create_user(username=email, email=email, password=password)
            user.save()

            messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect("login")

    return render(request, "core/register.html")

def password_reset_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        messages.success(request, f"Se enviaron instrucciones de recuperación al correo {email} (simulado).")
        return redirect("login")  

    return render(request, "core/password_reset.html")


