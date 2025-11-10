# core/forms.py

from django import forms
from django.core.exceptions import ValidationError
import re

from .models import Device, Category


# =============================
# Formulario de Device (CRUD)
# =============================

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        # SOLO campos que existen en el modelo Device
        fields = [
            "name",
            "category",
            "zone",
        ]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise ValidationError("El nombre es obligatorio.")
        if len(name) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        return name


# =============================
# Formulario de Category (CRUD)
# =============================

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        # Tu modelo Category solo tiene name
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise ValidationError("El nombre es obligatorio.")
        if len(name) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        return name


# =============================
# Formulario de Perfil de Usuario
# =============================

class ProfileForm(forms.Form):
    name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
    )
    email = forms.EmailField(
        label="Correo",
        required=True,
    )
    phone = forms.CharField(
        label="Teléfono",
        required=False,
    )
    avatar = forms.ImageField(
        label="Avatar",
        required=False,
    )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone:
            # validamos formato simple: solo números, +, espacios y guiones
            if not re.match(r"^[0-9+\-\s]+$", phone):
                raise ValidationError(
                    "El teléfono solo puede contener números, +, espacios y guiones."
                )
        return phone

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            # Máx 2MB
            max_size = 2 * 1024 * 1024
            if avatar.size > max_size:
                raise ValidationError("El avatar no puede superar los 2MB.")
        return avatar


# =============================
# Formulario de cambio de contraseña
# =============================

class PasswordChangeCustomForm(forms.Form):
    current_password = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput,
        required=True,
    )
    new_password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput,
        required=True,
    )
    confirm_password = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput,
        required=True,
    )

    def clean_new_password(self):
        pwd = self.cleaned_data.get("new_password", "")

        # Validaciones mínimas:
        # - longitud >= 8
        # - al menos 1 mayúscula
        # - al menos 1 número
        if len(pwd) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r"[A-Z]", pwd):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r"[0-9]", pwd):
            raise ValidationError("La contraseña debe contener al menos un número.")

        return pwd

    def clean(self):
        cleaned = super().clean()
        pwd1 = cleaned.get("new_password")
        pwd2 = cleaned.get("confirm_password")

        if pwd1 and pwd2 and pwd1 != pwd2:
            self.add_error("confirm_password", "Las contraseñas nuevas no coinciden.")

        return cleaned
