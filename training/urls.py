from django.urls import path
from .views import training_list, course_enroll, my_trainings

app_name = "training"

urlpatterns = [
    path("", training_list, name="training_list"),
    path("enroll/<int:course_id>/", course_enroll, name="course_enroll"),
    path("my-trainings/", my_trainings, name="my_trainings"),
]
