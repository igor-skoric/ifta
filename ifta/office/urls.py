from django.urls import path
from . import views

app_name = "office"

urlpatterns = [
    path("map/", views.office_map, name="office_map"),
    path("people/", views.people_list, name="people_list"),
    path("people/import/", views.people_import_excel, name="people_import"),
    path("people/new/", views.people_create, name="people_create"),
    path("people/<str:employee_id>/edit/", views.people_edit, name="people_edit"),
    path("people/<str:employee_id>/", views.people_profile, name="people_profile"),
    path("inventory/", views.inventory_list, name="inventory_list"),
    path("inventory/new/", views.inventory_create, name="inventory_create"),
    path("inventory/<str:asset_id>/edit/", views.inventory_edit, name="inventory_edit"),
    path("inventory/<str:asset_id>/delete/", views.inventory_delete, name="inventory_delete"),
    path("inventory/<str:asset_id>/", views.inventory_detail, name="inventory_detail"),
    path("people-inventory/", views.people_inventory, name="people_inventory"),
]
