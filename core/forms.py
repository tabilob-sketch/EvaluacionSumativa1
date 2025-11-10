# core/forms.py

from django import forms
from django.contrib.auth.models import User
from .models import Account, Device, Category

# Si ya tienes DeviceForm y CategoryForm, déjalos.
# Solo te dejo un ejemplo de DeviceForm con validaciones simples:

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["name", "category", "zone", "status"]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("El nombre es obligatorio.")
        return name


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]


class ProfileForm(forms.Form):
    name = forms.CharField(label="Nombre", max_length=150)
    email = forms.EmailField(label="Correo")
    phone = forms.CharField(label="Teléfono", max_length=30, required=False)
    avatar = forms.ImageField(label="Avatar", required=False)

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError("La imagen no puede pesar más de 2 MB.")
            if avatar.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise forms.ValidationError("Formato de imagen inválido. Usa JPG, PNG o WEBP.")
        return avatar


class PasswordChangeCustomForm(forms.Form):
    current_password = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput
    )
    new_password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput,
        help_text="Mínimo 8 caracteres, 1 mayúscula y 1 número."
    )
    confirm_password = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput
    )

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")

        if new and confirm and new != confirm:
            self.add_error("confirm_password", "Las contraseñas no coinciden.")

        # Validaciones mínimas
        if new:
            if len(new) < 8:
                self.add_error("new_password", "Debe tener al menos 8 caracteres.")
            if not any(c.isupper() for c in new):
                self.add_error("new_password", "Debe tener al menos una mayúscula.")
            if not any(c.isdigit() for c in new):
                self.add_error("new_password", "Debe tener al menos un número.")

        return cleaned
