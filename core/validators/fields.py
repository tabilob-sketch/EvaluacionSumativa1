from django.core.exceptions import ValidationError


def validate_not_empty(value, field_name="Campo"):
    if not value or not str(value).strip():
        raise ValidationError(f"{field_name} no puede estar vacío.")


def validate_min_length(value, min_len, field_name="Campo"):
    if len(str(value)) < min_len:
        raise ValidationError(f"{field_name} debe tener al menos {min_len} caracteres.")


def validate_numeric(value, field_name="Campo"):
    try:
        float(value)
    except ValueError:
        raise ValidationError(f"{field_name} debe ser numérico.")


def validate_range(value, min_value=None, max_value=None, field_name="Campo"):
    if min_value is not None and value < min_value:
        raise ValidationError(f"{field_name} no puede ser menor que {min_value}.")
    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} no puede ser mayor que {max_value}.")
