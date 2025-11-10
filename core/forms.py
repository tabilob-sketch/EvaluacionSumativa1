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


# core/forms.py  (añade al final o reemplaza la parte de ProfileForm)
from django import forms

# core/forms.py
from django import forms

# --- (Si ya tienes otras clases ModelForm, mantenlas arriba) ---
# Aquí solo añadimos ProfileForm para edición de perfil.

class ProfileForm(forms.Form):
    name = forms.CharField(max_length=150, required=True, label="Nombre")
    email = forms.EmailField(required=True, label="Correo")
    phone = forms.CharField(max_length=30, required=False, label="Teléfono")
    avatar = forms.ImageField(required=False, label="Avatar")

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("El nombre no puede quedar vacío.")
        return name

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar:
            return avatar
        # Validaciones: tamaño y tipo MIME
        max_mb = 2
        if avatar.size > max_mb * 1024 * 1024:
            raise forms.ValidationError(f"El avatar no puede superar {max_mb} MB.")
        valid_mimes = ("image/jpeg", "image/png", "image/webp")
        content_type = getattr(avatar, "content_type", "")
        if content_type not in valid_mimes:
            raise forms.ValidationError("Formato no soportado. Usa JPG, PNG o WEBP.")
        return avatar



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
