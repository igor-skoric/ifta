from django.urls import path

from . import views

app_name = "leave"

urlpatterns = [
    path("", views.leave_dashboard, name="dashboard"),
    path("balances/", views.leave_balances, name="balances"),
    path("allowance/<int:pk>/update/", views.leave_allowance_update_inline, name="allowance_update_inline"),
    path("new/", views.leave_create, name="create"),
    path("allowance/", views.leave_allowance_upsert, name="allowance"),
    path("<int:pk>/edit/", views.leave_edit, name="edit"),
    path("<int:pk>/delete/", views.leave_delete, name="delete"),
]

