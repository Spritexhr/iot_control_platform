from django.urls import path

from . import views

urlpatterns = [
    path("snapshot", views.snapshot, name="eb-plant-snapshot"),
    path("stream", views.stream, name="eb-plant-stream"),
    path("disturbance", views.disturbance, name="eb-plant-disturbance"),
]
