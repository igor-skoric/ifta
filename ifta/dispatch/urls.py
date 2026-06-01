from django.urls import path

from . import views

app_name = "dispatch"

urlpatterns = [
    path("", views.planner, name="planner"),
    path("drivers/import/sample/", views.driver_import_sample, name="driver_import_sample"),
    path("drivers/import/", views.driver_import, name="driver_import"),
    path("drivers/new/", views.driver_create, name="driver_create"),
    path("drivers/<int:pk>/edit/", views.driver_edit, name="driver_edit"),
    path("drivers/<int:pk>/assign/", views.driver_assign_equipment, name="driver_assign_equipment"),
    path(
        "drivers/<int:driver_pk>/unavailability/new/",
        views.driver_unavailability_create,
        name="driver_unavailability_create",
    ),
    path(
        "drivers/<int:driver_pk>/unavailability/<int:pk>/edit/",
        views.driver_unavailability_edit,
        name="driver_unavailability_edit",
    ),
    path(
        "drivers/<int:driver_pk>/unavailability/<int:pk>/delete/",
        views.driver_unavailability_delete,
        name="driver_unavailability_delete",
    ),
    path("drivers/<int:pk>/", views.driver_detail, name="driver_detail"),
    path("assignments/<int:pk>/end/", views.assignment_end, name="assignment_end"),
    path("drivers/", views.driver_list, name="driver_list"),
    path("trailers/new/", views.trailer_create, name="trailer_create"),
    path("trailers/<int:pk>/edit/", views.trailer_edit, name="trailer_edit"),
    path("trailers/<int:pk>/assign/", views.trailer_assign_equipment, name="trailer_assign_equipment"),
    path("trailers/<int:pk>/", views.trailer_detail, name="trailer_detail"),
    path("trailers/", views.trailer_list, name="trailer_list"),
    path("trucks/new/", views.truck_create, name="truck_create"),
    path("trucks/<int:pk>/edit/", views.truck_edit, name="truck_edit"),
    path("trucks/<int:pk>/assign/", views.truck_assign_equipment, name="truck_assign_equipment"),
    path("trucks/<int:pk>/samsara-panel/", views.truck_detail_samsara_panel, name="truck_samsara_panel"),
    path("trucks/<int:pk>/", views.truck_detail, name="truck_detail"),
    path("trucks/", views.truck_list, name="truck_list"),
    path("statistics/", views.dispatch_statistics, name="statistics"),
    path("statistics/leaderboard/", views.dispatcher_ranking, name="dispatcher_ranking"),
    path("loads/", views.load_list, name="load_list"),
    path("loads/new/", views.load_create, name="load_create"),
    path("loads/<int:pk>/edit/", views.load_edit, name="load_edit"),
    path("loads/<int:pk>/status/", views.load_status_update, name="load_status_update"),
    path("loads/<int:pk>/docs-status/", views.load_docs_status_update, name="load_docs_status_update"),
    path("loads/<int:pk>/comments/", views.load_comments, name="load_comments"),
    path("loads/<int:pk>/comments/add/", views.load_comment_create, name="load_comment_create"),
    path("loads/<int:pk>/", views.load_detail, name="load_detail"),
    # Legacy trip URLs (redirect)
    path("trips/", views.trip_list_redirect, name="trip_list"),
    path("trips/new/", views.trip_create_redirect, name="trip_create"),
    path("trips/<int:pk>/edit/", views.trip_edit_redirect, name="trip_edit"),
    path("trips/<int:pk>/status/", views.trip_status_update_redirect, name="trip_status_update"),
    path("trips/<int:pk>/", views.trip_detail_redirect, name="trip_detail"),
    path("trips/<int:trip_pk>/loads/", views.trip_load_add_redirect, name="trip_load_add"),
    path(
        "trips/<int:trip_pk>/loads/<int:load_pk>/status/",
        views.trip_load_status_redirect,
        name="trip_load_status_update",
    ),
    path(
        "trips/<int:trip_pk>/loads/<int:load_pk>/edit/",
        views.trip_load_edit_redirect,
        name="trip_load_edit",
    ),
]
