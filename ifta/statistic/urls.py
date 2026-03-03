# statistic/urls.py
from django.urls import path
from .views import WeeklyDriverDataAPI, WeeklyDayDataListView, DispatcherSheetRowListAPIView

urlpatterns = [
    path('weekly-driver-data/', WeeklyDriverDataAPI, name='weekly-driver-data'),
    path('weekly-statistic/', WeeklyDayDataListView.as_view(), name='weekly-data-list'),
    path("dispatchers/", DispatcherSheetRowListAPIView.as_view(), name="dispatcher-list"),

]
