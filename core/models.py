from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError



class Organization(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Zone(models.Model):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Device(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def clean(self):
        """
        Validación de coherencia multi-tenant:
        - category y zone deben pertenecer a la MISMA organization que el device.
        """
        errors = {}
        if self.category and self.organization and self.category.organization_id != self.organization_id:
            errors["category"] = "Category must belong to the same Organization as Device."
        if self.zone and self.organization and self.zone.organization_id != self.organization_id:
            errors["zone"] = "Zone must belong to the same Organization as Device."
        if errors:
            raise ValidationError(errors)

    class Meta:
        #  evita duplicar nombres de dispositivos dentro de una misma organización
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="uniq_device_name_per_org"),
        ]
        ordering = ("name",)  # orden por defecto útil en admin/listas


class Measurement(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        """
        Validación de negocio:
        - value requerido y dentro de rango razonable (0..1000 como ejemplo).
        """
        if self.value is None:
            raise ValidationError({"value": "Value is required."})
        if not (0 <= self.value <= 1000):
            raise ValidationError({"value": "Value must be between 0 and 1000."})

    class Meta:
        ordering = ("-created_at",)



class Alert(models.Model):
    PRIORITY_CHOICES = [
        ("grave", "Grave"),
        ("alto", "Alto"),
        ("medio", "Mediano"),
    ]
    device = models.ForeignKey("Device", on_delete=models.CASCADE)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medio")
    acknowledged = models.BooleanField(default=False)  # NUEVO
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device.name} - {self.priority}"



class Account(models.Model):
    class Role(models.TextChoices):
        ORG_ADMIN = "ORG_ADMIN", "Org Admin"
        VERIFIER  = "VERIFIER", "Verifier"
        MEMBER    = "MEMBER", "Member"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="account")
    organization = models.ForeignKey("Organization", on_delete=models.PROTECT, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    def __str__(self):
        org = self.organization.name if self.organization else "No org"
        return f"{self.user.username} ({org}) — {self.role}"

    