from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.generic import RedirectView
from .views import (
    export_ifta,
    export_ifta_excel,
    fuel_efficiency_chart,
    ifta_list,
    import_miles_files,
    signout,
    vehicle_mpg,
    vehicle_pivot_report,
    people_inventory,
)

urlpatterns = [
      path('', ifta_list, name='home'),
      path('vehicle_mpg/', vehicle_mpg, name='vehicle-mpg'),
      path('upload/', import_miles_files, name='upload'),
      path('report', vehicle_pivot_report, name='report'),
      path('upload-fuel/', import_miles_files, name='upload-fuel'),
      path('export_ifta/', export_ifta, name='export_ifta'),
      path('export_ifta_excel/', export_ifta_excel, name='export_ifta_excel'),
      path('fuel_chart/', fuel_efficiency_chart, name='fuel-chart'),
      path('people-inventory/', people_inventory, name='people-inventory'),
      path('signout/', signout, name='signout'),

      # Statistics (canonical: /statistics/1/ …)
      path('1/', RedirectView.as_view(url='/statistics/1/', permanent=True), name='statistic'),
      path('2/', RedirectView.as_view(url='/statistics/2/', permanent=True), name='statistic2'),
      path('3/', RedirectView.as_view(url='/statistics/3/', permanent=True), name='statistic3'),
      path('4/', RedirectView.as_view(url='/statistics/', permanent=True), name='weekly_analytics'),

      # path('report-miles/export/', ifta_export_excel, name='export-miles'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
