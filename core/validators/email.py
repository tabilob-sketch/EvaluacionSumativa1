import re
from django.core.exceptions import ValidationError

# Dominios aceptados (puedes agregar más)
VALID_DOMAINS = (
    ".com", ".cl", ".net", ".org", ".edu", ".gov", ".io", ".co", ".info",
)

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

def validate_email_format(value):
    """
    Valida que el correo tenga un formato correcto.
    """
    if not EMAIL_REGEX.match(value):
        raise ValidationError("El correo no tiene un formato válido.")

def validate_email_domain(value):
    """
    Valida que el correo termine en un dominio permitido (.cl, .com, etc.)
    """
    if not any(value.endswith(d) for d in VALID_DOMAINS):
        raise ValidationError(
            f"El dominio del correo debe ser uno de: {', '.join(VALID_DOMAINS)}"
        )
