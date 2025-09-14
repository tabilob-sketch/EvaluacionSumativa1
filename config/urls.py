from django.contrib import admin
from django.urls import path, include   # 👈 usamos include, no importamos views aquí

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),     # 👈 mandamos la raíz al app "core"
]