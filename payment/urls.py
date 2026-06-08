from django.urls import path
from .views import (confirm_group_payment, payment_page,payment_group,confirm_payment,payment_success,make_payment_api,)
from .views import (
    payment_page,
    # start_payment,
    confirm_payment,
    payment_success,
    make_payment_api,
)

app_name = "payment"   # 🔥 REQUIRED for namespacing

urlpatterns = [
    path("group/", payment_group, name="payment_group"),
    path("confirm-group/",confirm_group_payment,name="confirm_group_payment"),
    path("<int:appointment_id>/", payment_page, name="payment_page"),
    path("confirm/<int:appointment_id>/", confirm_payment, name="payment_confirm"),
    path("success/", payment_success, name="payment_success"),

    # API (future mobile app)
    path("api/make-payment/", make_payment_api, name="make_payment_api"),
]
