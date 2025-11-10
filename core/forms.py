# core/forms.py

from django import forms
from django.core.exceptions import ValidationError

from .models import Device, Category


class DeviceForm(forms.ModelForm):
    """
    Formulario para crear/editar dispositivos.
    SOLO usa campos que sabemos que existen en el modelo Device
    (por lo que vimos en tus errores previos: name, category, zone).
    """

    class Meta:
        model = Device
        fields = ["name", "category", "zone"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("El nombre no puede estar vacío.")
        return name


class CategoryForm(forms.ModelForm):
    """
    Formulario simple para categorías.
    Solo usamos el campo 'name', la organization la fija la vista.
    """

    class Meta:
        model = Category
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("El nombre no puede estar vacío.")
        return name


class ProfileForm(forms.Form):
    """
    Form para editar perfil del usuario:
    - name (username)
    - email
    - phone
    - avatar (opcional)
    """

    name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Correo",
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        label="Teléfono",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    avatar = forms.ImageField(
        label="Avatar",
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )


class PasswordChangeCustomForm(forms.Form):
    """
    Form para cambio de contraseña con
    validaciones mínimas:
    - longitud >= 8
    - al menos una mayúscula
    - al menos un número
    """

    current_password = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    new_password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    confirm_password = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")

        if new and confirm and new != confirm:
            raise ValidationError("Las contraseñas nuevas no coinciden.")

        if new:
            if len(new) < 8:
                raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
            if not any(c.isupper() for c in new):
                raise ValidationError("La contraseña debe tener al menos una mayúscula.")
            if not any(c.isdigit() for c in new):
                raise ValidationError("La contraseña debe tener al menos un número.")

        return cleaned
