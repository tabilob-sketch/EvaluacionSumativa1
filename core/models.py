from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from core.validators import (
    validate_not_empty,
    validate_min_length,
    validate_numeric,
    validate_range,
    validate_same_organization,
    validate_email_format,
    validate_phone_format,
    validate_image_size,
    validate_image_extension,
)


# =========================
# ORGANIZATION
# =========================

class Organization(models.Model):
    name = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        validate_not_empty(self.name, "Nombre de la organización")
        validate_min_length(self.name, 3, "Nombre de la organización")

    def __str__(self):
        return self.name


# =========================
# CATEGORY
# =========================

class Category(models.Model):
    name = models.CharField(max_length=20)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="categories",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        validate_not_empty(self.name, "Nombre de la categoría")
        if not self.organization:
            raise ValidationError({"organization": "Debe seleccionar una organización válida."})

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


# =========================
# ZONE
# =========================

class Zone(models.Model):
    name = models.CharField(max_length=100)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="zones",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        validate_not_empty(self.name, "Nombre de la zona")
        if not self.organization:
            raise ValidationError({"organization": "Debe seleccionar una organización válida."})

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


# =========================
# DEVICE
# =========================

class Device(models.Model):
    name = models.CharField(max_length=100)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="devices",
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name="devices",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="devices",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}

        # Nombre
        try:
            validate_not_empty(self.name, "Nombre del dispositivo")
            validate_min_length(self.name, 3, "Nombre del dispositivo")
        except ValidationError as e:
            errors["name"] = e.message

        # Organización obligatoria
        if not self.organization:
            errors["organization"] = "El dispositivo debe estar asociado a una organización."

        # Category y Zone deben pertenecer a la misma organización
        try:
            if self.category and self.organization:
                validate_same_organization(self, self.category, "category")
        except ValidationError as e:
            errors.update(e.message_dict)

        try:
            if self.zone and self.organization:
                validate_same_organization(self, self.zone, "zone")
        except ValidationError as e:
            errors.update(e.message_dict)

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name

    class Meta:
        # evita duplicar nombres de dispositivos dentro de una misma organización
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_device_name_per_org",
            ),
        ]
        ordering = ("name",)


# =========================
# MEASUREMENT
# =========================

class Measurement(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        errors = {}

        # numérico y rango razonable
        try:
            validate_numeric(self.value, "Valor de la medición")
        except ValidationError as e:
            errors["value"] = e.message

        try:
            validate_range(self.value, min_value=0, max_value=10000, field_name="Valor de la medición")
        except ValidationError as e:
            errors["value"] = e.message  # pisa el anterior si existe

        if errors:
            raise ValidationError(errors)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.device.name} = {self.value}"


# =========================
# ALERT
# =========================

class Alert(models.Model):
    PRIORITY_CHOICES = [
        ("grave", "Grave"),
        ("alto", "Alto"),
        ("medio", "Mediano"),
    ]

    device = models.ForeignKey("Device", on_delete=models.CASCADE)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medio")
    acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        validate_not_empty(self.message, "Mensaje de alerta")
        # La prioridad ya está restringida por choices, pero validamos por si acaso
        valid_keys = [c[0] for c in self.PRIORITY_CHOICES]
        if self.priority not in valid_keys:
            raise ValidationError({"priority": "Prioridad inválida."})

    def __str__(self):
        return f"{self.device.name} - {self.priority}"


# =========================
# ACCOUNT
# =========================

class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    class Role(models.TextChoices):
        ORG_ADMIN = "ORG_ADMIN", "Administrador"
        VERIFIER = "VERIFIER", "Verificador"
        MEMBER = "MEMBER", "Miembro"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    def clean(self):
        errors = {}

        # Validar email del usuario (si existe)
        if self.user and self.user.email:
            try:
                validate_email_format(self.user.email)
            except ValidationError as e:
                errors["user"] = f"Correo del usuario inválido: {e.message}"

        # Teléfono
        try:
            validate_phone_format(self.phone)
        except ValidationError as e:
            errors["phone"] = e.message

        # Avatar
        if self.avatar:
            try:
                validate_image_size(self.avatar, max_mb=2)
            except ValidationError as e:
                errors["avatar"] = e.message
            try:
                validate_image_extension(self.avatar)
            except ValidationError as e:
                errors["avatar"] = e.message

        # Rol
        if self.role not in Account.Role.values:
            errors["role"] = "Rol inválido."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.user.username} ({self.role})"
