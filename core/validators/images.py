from django.core.exceptions import ValidationError


def validate_image_size(image, max_mb=2):
    limit = max_mb * 1024 * 1024
    if image.size > limit:
        raise ValidationError(f"La imagen no debe superar {max_mb} MB.")


def validate_image_extension(image):
    valid_extensions = (".jpg", ".jpeg", ".png")
    if not image.name.lower().endswith(valid_extensions):
        raise ValidationError("Solo se permiten imágenes JPG o PNG.")
