from django.urls import path
from . import views


urlpatterns = [
    path("map/", views.office_map, name="office_map"),
]
