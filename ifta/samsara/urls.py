from django.urls import path

from . import views

app_name = "samsara"

urlpatterns = [
    path("", views.samsara_dashboard, name="dashboard"),
    path("vehicles/<str:samsara_id>/trips/", views.vehicle_trip_list, name="vehicle_trip_list"),
    path("vehicles/<str:samsara_id>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/", views.vehicle_list, name="vehicle_list"),
    path("drivers/<str:samsara_id>/trips/", views.driver_trip_list, name="driver_trip_list"),
    path("trips/<str:samsara_id>/", views.trip_detail, name="trip_detail"),
    path("drivers/<str:samsara_id>/", views.driver_detail, name="driver_detail"),
    path("drivers/", views.driver_list, name="driver_list"),
    path("sync/vehicles/", views.sync_vehicles, name="sync_vehicles"),
    path("sync/drivers/", views.sync_drivers, name="sync_drivers"),
    path("sync/trips/", views.sync_trips, name="sync_trips"),
]
