# core/forms.py
from django import forms
from .models import Device, Category


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["name", "category", "zone"]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return name


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return name


class ProfileForm(forms.Form):
    name = forms.CharField(
        label="Nombre",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    email = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    phone = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    avatar = forms.FileField(
        label="Avatar",
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"})
    )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return name


class PasswordChangeCustomForm(forms.Form):
    current_password = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    new_password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    confirm_password = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")

        # Coincidencia
        if new and confirm and new != confirm:
            self.add_error("confirm_password", "Las contraseñas no coinciden.")

        # Reglas básicas
        if new:
            if len(new) < 8:
                self.add_error("new_password", "La contraseña debe tener al menos 8 caracteres.")
            if not any(c.isupper() for c in new):
                self.add_error("new_password", "La contraseña debe tener al menos una mayúscula.")
            if not any(c.isdigit() for c in new):
                self.add_error("new_password", "La contraseña debe tener al menos un número.")

        return cleaned
