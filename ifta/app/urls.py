from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import  ifta_list, vehicle_pivot_report,  import_miles_files, export_ifta, export_ifta_excel, vehicle_mpg, fuel_efficiency_chart, signout, statistic, tv_rotator, statistic2

urlpatterns = [
      path('', ifta_list, name='home'),
      path('vehicle_mpg/', vehicle_mpg, name='vehicle-mpg'),
      path('upload/', import_miles_files, name='upload'),
      path('report', vehicle_pivot_report, name='report'),
      path('upload-fuel/', import_miles_files, name='upload-fuel'),
      path('export_ifta/', export_ifta, name='export_ifta'),
      path('export_ifta_excel/', export_ifta_excel, name='export_ifta_excel'),
      path('fuel_chart/', fuel_efficiency_chart, name='fuel-chart'),
      path('signout/', signout, name='signout'),

      # Statistics
      path("tv/", tv_rotator, name="tv"),
      path('statistic/', statistic, name='statistic'),
      path("statistic2/", statistic2, name="statistic2")  # napraviš

      # path('report-miles/export/', ifta_export_excel, name='export-miles'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
