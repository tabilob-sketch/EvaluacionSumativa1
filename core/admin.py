from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from .models import Organization, Category, Zone, Device, Measurement, Alert, Account

# =======================
# Helpers de rol / org
# =======================
def user_org(user):
    acc = getattr(user, "account", None)
    return acc.organization if acc and acc.organization_id else None

def is_org_admin(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.ORG_ADMIN)

def is_member(user):
    acc = getattr(user, "account", None)
    return bool(acc and acc.role == Account.Role.MEMBER)


# ==========================================
# Inline para editar Account en el UserAdmin
# ==========================================
class AccountInline(admin.StackedInline):
    model = Account
    can_delete = False
    fk_name = "user"
    extra = 0
    fields = ("organization", "role")
    verbose_name_plural = "Account (Organization & Role)"


class UserAdmin(DjangoUserAdmin):
    inlines = [AccountInline]
    list_display = ("username", "email", "is_staff", "is_superuser")

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        # Si quieres permitir que org_admin cree usuarios, cambia a True aquí:
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        # Si quisieras permitir que org_admin edite solo usuarios de su org, implementa aquí.
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False


# Reemplaza el admin de User nativo
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ==========================================
# Mixin base: scoping por org + superuser libre
# ==========================================
class OrgScopedAdmin(admin.ModelAdmin):
    """
    - Superuser: todo (sin restricciones).
    - Org Admin: CRUD solo dentro de su Organization.
    - Member: solo lectura de su Organization.
    """

    # 1) Filtra queryset por Organization (no aplica a superuser)
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

    # 2) Permisos CRUD
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return bool(user_org(request.user))

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        # Permite alta a org_admin
        return is_org_admin(request.user)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if is_org_admin(request.user):
            if obj is None:
                return True
            org = user_org(request.user)
            if hasattr(obj, "organization"):
                return obj.organization_id == getattr(org, "id", None)
            if hasattr(obj, "device"):
                return obj.device.organization_id == getattr(org, "id", None)
        return False  # member read-only

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        # Solo org_admin y dentro de su org
        return self.has_change_permission(request, obj)

    # 3) Limitar choices de ForeignKey por org (no aplica a superuser)
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

    # 4) Read-only fields
    def get_readonly_fields(self, request, obj=None):
        # Superuser: NINGÚN campo readonly
        if request.user.is_superuser:
            return []
        ro = list(super().get_readonly_fields(request, obj))
        if is_member(request.user):
            # Member: todo readonly
            if obj:
                return [f.name for f in obj._meta.fields]
            return ro
        # Org Admin: organization no editable directamente (se setea en save)
        if "organization" in [f.name for f in self.model._meta.fields]:
            ro.append("organization")
        return ro

    # 5) Setear organization automáticamente para org_admin
    def save_model(self, request, obj, form, change):
        if request.user.is_superuser:
            return super().save_model(request, obj, form, change)
        org = user_org(request.user)
        if hasattr(obj, "organization") and org:
            obj.organization = org
        super().save_model(request, obj, form, change)


# ===========================
# Admins por cada modelo core
# ===========================
@admin.register(Organization)
class OrganizationAdmin(OrgScopedAdmin):
    # Si quieres que solo superuser edite Organizations, mantenlo así:
    def has_add_permission(self, request):
        return request.user.is_superuser
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    list_display = ("id", "name", "created_at", "updated_at")
    list_display_links = ("name",)  # ← link a formulario de cambio
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


@admin.register(Device)
class DeviceAdmin(OrgScopedAdmin):
    list_display = ("id", "name", "category", "zone", "organization", "created_at")
    list_display_links = ("name",)
    list_select_related = ("category", "zone", "organization")
    list_filter = ("organization", "category", "zone")
    search_fields = ("name", "category__name", "zone__name", "organization__name")
    ordering = ("name",)


@admin.register(Measurement)
class MeasurementAdmin(OrgScopedAdmin):
    list_display = ("id", "device", "value", "created_at")
    list_display_links = ("id",)
    list_select_related = ("device",)
    list_filter = ("device__organization",)
    search_fields = ("device__name",)
    ordering = ("-created_at",)


@admin.register(Alert)
class AlertAdmin(OrgScopedAdmin):
    list_display = ("id", "device", "priority", "created_at")
    list_display_links = ("id",)
    list_select_related = ("device",)
    list_filter = ("priority", "device__organization")
    search_fields = ("device__name", "message")
    ordering = ("-created_at",)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "organization", "role")
    list_display_links = ("user",)   # clic en user para editar Account
    list_select_related = ("user", "organization")
    search_fields = ("user__username", "user__email", "organization__name")
    list_filter = ("organization", "role")


