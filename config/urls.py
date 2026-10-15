# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("courses/", include("courses.urls")),
    path("expenses/", include("expenses.urls")),
    path("routines/", include("routines.urls")),
    path("", include("dashboard.urls")),
    path("staff/", include("analytics_app.urls")),
]

# serve uploaded files in dev only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)