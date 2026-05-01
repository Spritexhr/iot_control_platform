from django.urls import path

from . import views

urlpatterns = [
    path("ping/", views.ping, name="data-viz-ping"),
    path("sources/", views.sources, name="data-viz-sources"),
    path("series/", views.series, name="data-viz-series"),
]
