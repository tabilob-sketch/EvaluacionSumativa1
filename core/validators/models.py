from django.core.exceptions import ValidationError


def validate_same_organization(obj, field_obj, field_name):
    if field_obj and obj.organization:
        if field_obj.organization_id != obj.organization_id:
            raise ValidationError({
                field_name: f"{field_name} no pertenece a esta organización."
            })
