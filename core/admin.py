from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse
import csv

from .models import (
    Organization,
    Category,
    Zone,
    Device,
    Measurement,
    Alert,
    Account,
)

# ============================================================
# Helpers de rol / organización
# ============================================================

def user_org(user):
    """
    Devuelve la Organization asociada al usuario (si tiene Account y org).
    """
    acc = getattr(user, "account", None)
    if acc and acc.organization_id:
        return acc.organization
    return None


def is_org_admin(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.ORG_ADMIN)


def is_verifier(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.VERIFIER)


def is_member(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.MEMBER)


# ============================================================
# User + AccountInline (gestión de rol y organización del usuario)
# ============================================================

class AccountInline(admin.StackedInline):
    model = Account
    can_delete = False
    fk_name = "user"
    extra = 0
    fields = ("organization", "role")
    verbose_name_plural = "Account (Organization & Role)"


class UserAdmin(DjangoUserAdmin):
    """
    Solo el superuser puede crear/editar/borrar usuarios desde el admin.
    Aquí se ve el inline de Account para asignar Organization + Role.
    """
    inlines = [AccountInline]
    list_display = ("username", "email", "is_staff", "is_superuser")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Reemplaza el admin nativo de User
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ============================================================
# Mixin base: OrgScopedAdmin
#   - Aplica scoping por Organization para NO superusers
#   - Controla permisos view/add/change/delete para ORG_ADMIN / VERIFIER / MEMBER
# ============================================================

class OrgScopedAdmin(admin.ModelAdmin):
    """
    - Superuser: ve y modifica todo.
    - Org Admin: CRUD dentro de su organización.
    - Verifier: por defecto solo lectura (se puede afinar en alertas).
    - Member: solo lectura.
    """

    # 1) Filtrar por organización
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        org = user_org(request.user)
        if not org:
            return qs.none()

        # FK directa a Organization
        if hasattr(self.model, "organization"):
            return qs.filter(organization=org)

        # Modelos que cuelgan de Device -> Organization
        if hasattr(self.model, "device"):
            return qs.filter(device__organization=org)

        return qs.none()

    # 2) Permiso para ver
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        # Si tiene organización, puede ver
        return bool(user_org(request.user))

    # 3) Permiso para agregar
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        # Solo ORG_ADMIN puede crear
        return is_org_admin(request.user)

    # 4) Permiso para cambiar
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if is_org_admin(request.user):
            if obj is None:
                return True
            org = user_org(request.user)
            if not org:
                return False
            if hasattr(obj, "organization"):
                return obj.organization_id == org.id
            if hasattr(obj, "device"):
                return obj.device.organization_id == org.id
        # Verifier y Member: por defecto sin permisos de cambio (se ajusta por modelo)
        return False

    # 5) Permiso para borrar
    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        # Por defecto, solo ORG_ADMIN (mismo criterio que change)
        return self.has_change_permission(request, obj)

    # 6) Limitar choices de ForeignKey a la organización del usuario
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.user.is_superuser:
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        org = user_org(request.user)
        if not org:
            kwargs["queryset"] = db_field.remote_field.model.objects.none()
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        model = db_field.remote_field.model
        try:
            if model is Organization:
                kwargs["queryset"] = Organization.objects.filter(id=org.id)
            elif model is Category:
                kwargs["queryset"] = Category.objects.filter(organization=org)
            elif model is Zone:
                kwargs["queryset"] = Zone.objects.filter(organization=org)
            elif model is Device:
                kwargs["queryset"] = Device.objects.filter(organization=org)
        except Exception:
            pass

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 7) Campos solo lectura según rol
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return []

        ro = list(super().get_readonly_fields(request, obj))

        # Member: todo read-only
        if is_member(request.user):
            if obj:
                return [f.name for f in obj._meta.fields]
            return ro

        # Verifier: por defecto, read-only en todos los modelos (ajustamos en AlertAdmin)
        if is_verifier(request.user):
            if obj:
                return [f.name for f in obj._meta.fields]
            return ro

        # Org Admin: no puede cambiar organization directamente (la fijamos en save)
        if "organization" in [f.name for f in self.model._meta.fields]:
            ro.append("organization")

        return ro

    # 8) Setear organization automáticamente para ORG_ADMIN
    def save_model(self, request, obj, form, change):
        if request.user.is_superuser:
            return super().save_model(request, obj, form, change)

        org = user_org(request.user)
        if hasattr(obj, "organization") and org:
            obj.organization = org

        super().save_model(request, obj, form, change)

    # 9) Ocultar módulo en index del admin si no tiene organización
    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return bool(user_org(request.user))


# ============================================================
# Admin de modelos
# ============================================================

@admin.register(Organization)
class OrganizationAdmin(OrgScopedAdmin):
    """
    Organization solo editable por superuser.
    """
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    list_display = ("id", "name", "created_at", "updated_at")
    list_display_links = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Category)
class CategoryAdmin(OrgScopedAdmin):
    list_display = ("id", "name", "organization", "created_at")
    list_display_links = ("name",)
    list_select_related = ("organization",)
    list_filter = ("organization",)
    search_fields = ("name", "organization__name")
    ordering = ("name",)


@admin.register(Zone)
class ZoneAdmin(OrgScopedAdmin):
    list_display = ("id", "name", "organization", "created_at")
    list_display_links = ("name",)
    list_select_related = ("organization",)
    list_filter = ("organization",)
    search_fields = ("name", "organization__name")
    ordering = ("name",)


class MeasurementInline(admin.TabularInline):
    model = Measurement
    extra = 0
    fields = ("value", "created_at")
    readonly_fields = ("created_at",)
    can_delete = True


@admin.register(Device)
class DeviceAdmin(OrgScopedAdmin):
    list_display = ("id", "name", "category", "zone", "organization", "created_at")
    list_display_links = ("name",)
    list_select_related = ("category", "zone", "organization")
    list_filter = ("organization", "category", "zone")
    search_fields = ("name", "category__name", "zone__name", "organization__name")
    ordering = ("name",)
    inlines = [MeasurementInline]


@admin.register(Measurement)
class MeasurementAdmin(OrgScopedAdmin):
    list_display = ("id", "device", "value", "created_at")
    list_select_related = ("device",)
    list_filter = ("device__organization",)
    search_fields = ("device__name",)
    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        # Ejecuta validaciones personalizadas definidas en clean()
        obj.full_clean()
        super().save_model(request, obj, form, change)


# ============================================================
# Acciones personalizadas para Alert
# ============================================================

@admin.action(description="Marcar prioridad como ALTA (alto)")
def mark_priority_high(modeladmin, request, queryset):
    updated = queryset.update(priority="alto")
    modeladmin.message_user(request, f"{updated} alertas actualizadas a prioridad ALTA.")


@admin.action(description="Exportar seleccionadas a CSV")
def export_alerts_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=alerts.csv"
    writer = csv.writer(response)
    writer.writerow(["ID", "Device", "Priority", "Message", "Created At"])
    for a in queryset.select_related("device"):
        writer.writerow([a.id, a.device.name, a.priority, a.message, a.created_at.isoformat()])
    return response


@admin.action(description="Marcar como atendidas")
def mark_as_acknowledged(modeladmin, request, queryset):
    updated = queryset.update(acknowledged=True)
    modeladmin.message_user(request, f"{updated} alerta(s) marcadas como atendidas.")


@admin.register(Alert)
class AlertAdmin(OrgScopedAdmin):
    list_display = ("id", "device", "priority", "acknowledged", "created_at")
    list_select_related = ("device",)
    list_filter = ("priority", "acknowledged", "device__organization")
    search_fields = ("device__name", "message")
    ordering = ("-created_at",)

    actions = [mark_as_acknowledged, mark_priority_high, export_alerts_csv]

    def has_change_permission(self, request, obj=None):
        """
        En Alert:
        - Superuser: todo.
        - ORG_ADMIN: puede editar/borrar sus alertas.
        - VERIFIER: puede editar alertas (por ejemplo, marcar acknowledged, cambiar prioridad).
        - MEMBER: solo lectura.
        """
        if request.user.is_superuser:
            return True

        if is_org_admin(request.user) or is_verifier(request.user):
            if obj is None:
                return True
            org = user_org(request.user)
            if not org:
                return False
            return obj.device.organization_id == org.id

        return False

    def has_delete_permission(self, request, obj=None):
        """
        Solo superuser y ORG_ADMIN pueden borrar alertas.
        Verifier no puede borrar.
        """
        if request.user.is_superuser:
            return True
        if is_org_admin(request.user):
            return super().has_change_permission(request, obj)
        return False


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "organization", "role")
    list_display_links = ("user",)
    list_select_related = ("user", "organization")
    search_fields = ("user__username", "user__email", "organization__name")
    list_filter = ("organization", "role")
