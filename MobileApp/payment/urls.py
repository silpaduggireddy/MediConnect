from django.urls import path
from .views import (
    payment_page,
    # start_payment,
    confirm_payment,
    payment_success,
    make_payment_api,
)

app_name = "payment"   # 🔥 REQUIRED for namespacing

urlpatterns = [
    path("<int:appointment_id>/", payment_page, name="payment_page"),
    path("confirm/<int:appointment_id>/", confirm_payment, name="payment_confirm"),
    path("success/", payment_success, name="payment_success"),

    # API (future mobile app)
    path("api/make-payment/", make_payment_api, name="make_payment_api"),
]
