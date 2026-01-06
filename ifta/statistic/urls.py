# statistic/urls.py
from django.urls import path
from .views import WeeklyDriverDataAPI, WeeklyDayDataListView

urlpatterns = [
    path('weekly-driver-data/', WeeklyDriverDataAPI, name='weekly-driver-data'),
    path('weekly-statistic/', WeeklyDayDataListView.as_view(), name='weekly-data-list'),
]
