from django.urls import path
from .views import (
    service_selection,
    online_consultation,
    clinic_consultation,
    training_list,
)

urlpatterns = [
    path("", service_selection, name="services"),
    path("online/", online_consultation, name="online-consultation"),
    path("clinic/", clinic_consultation, name="clinic-consultation"),
    path("training/", training_list, name="training"),
]

