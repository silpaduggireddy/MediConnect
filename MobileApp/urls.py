from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Core (home, post-login redirect)
    path("", include("core.urls")),

    # Authentication (OTP based)
    path("auth/", include("accounts.urls")),

    # Admin
    path("admin/", admin.site.urls),

    # Dashboards
    # path("dashboard/", include("dashboards.urls")),
    path("dashboard/staff/", include("staff.urls")),

    # App modules
    path("dashboard/doctor/", include("doctors.urls")),
    path("appointments/", include("appointments.urls")),
    path("payment/", include("payment.urls")),
    path("services/", include("services.urls")),
    path("training/", include("training.urls")),
]


urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)