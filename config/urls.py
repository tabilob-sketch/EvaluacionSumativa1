from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]

# Handler 404 global
handler404 = "core.views.custom_404"
