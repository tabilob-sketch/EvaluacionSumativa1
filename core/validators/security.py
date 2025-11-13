from django.core.exceptions import ValidationError


def validate_email_format(email):
    if "@" not in email or "." not in email:
        raise ValidationError("Debe ingresar un correo válido.")


def validate_phone_format(phone):
    if phone and not phone.replace("+", "").isdigit():
        raise ValidationError("El teléfono solo puede contener dígitos y '+'.")
