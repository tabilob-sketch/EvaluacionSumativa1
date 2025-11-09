from django import forms
from .models import Device, Category  


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["name", "category", "zone"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre del dispositivo",
            }),
            "category": forms.Select(attrs={"class": "form-select"}),
            "zone": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("El nombre no puede estar vacío.")
        return name


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nombre de la categoría",
            }),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("El nombre no puede estar vacío.")
        return name
