import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from core.models import Organization, Category, Zone, Device, Measurement, Alert

class Command(BaseCommand):
    help = "Populate database with sample data"

    def handle(self, *args, **kwargs):
        # lipio la base
        Organization.objects.all().delete()
        Category.objects.all().delete()
        Zone.objects.all().delete()
        Device.objects.all().delete()
        Measurement.objects.all().delete()
        Alert.objects.all().delete()

        #  organización
        org = Organization.objects.create(name="TechCorp")

        #  categorías
        categories = [
            Category.objects.create(name="Temperature Sensors", organization=org),
            Category.objects.create(name="Humidity Sensors", organization=org),
            Category.objects.create(name="Pressure Sensors", organization=org),
        ]

        #  zonas
        zones = [
            Zone.objects.create(name="Factory A", organization=org),
            Zone.objects.create(name="Factory B", organization=org),
        ]

        #  dispositivos
        devices = []
        for i in range(1, 11):
            device = Device.objects.create(
                name=f"Device {i}",
                category=random.choice(categories),
                zone=random.choice(zones),
                organization=org
            )
            devices.append(device)

        #  mediciones
        for device in devices:
            for _ in range(10):  # 10 mediciones por dispositivo
                Measurement.objects.create(
                    device=device,
                    value=round(random.uniform(10.0, 100.0), 2),
                    created_at=datetime.now() - timedelta(minutes=random.randint(1, 500))
                )

        #  alertas
        for device in devices[:5]:  # solo para algunos dispositivos
            d1 = Device.objects.first()
            Alert.objects.create(device=d1, message="Temperatura muy alta", priority="grave")
            Alert.objects.create(device=d1, message="Nivel de batería bajo", priority="alto")
            Alert.objects.create(device=d1, message="Chequeo rutinario", priority="medio")

        self.stdout.write(self.style.SUCCESS("✅ Sample data inserted successfully!"))
