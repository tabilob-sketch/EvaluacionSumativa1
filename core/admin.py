from django.contrib import admin
from .models import Organization, Category, Zone, Device, Measurement, Alert

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "organization")
    search_fields = ("name", "organization__name")
    list_filter = ("organization",)
    ordering = ("organization__name", "name")
    list_select_related = ("organization",)

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "organization")
    search_fields = ("name", "organization__name")
    list_filter = ("organization",)
    ordering = ("organization__name", "name")
    list_select_related = ("organization",)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "zone", "organization", "created_at")
    search_fields = ("name", "category__name", "zone__name", "organization__name")
    list_filter = ("organization", "category", "zone")
    ordering = ("organization__name", "name")
    list_select_related = ("organization", "category", "zone")

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "value", "created_at")
    search_fields = ("device__name",)
    list_filter = ("device__organization", "device__category", "device__zone")
    ordering = ("-created_at",)
    list_select_related = ("device", "device__organization", "device__category", "device__zone")

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "priority", "created_at")
    search_fields = ("device__name", "message")
    list_filter = ("priority", "device__organization")
    ordering = ("-created_at",)
    list_select_related = ("device", "device__organization")

class AccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "organization")
    list_select_related = ("user", "organization")
    search_fields = ("user__username", "user__email", "organization__name")
    list_filter = ("organization",)
