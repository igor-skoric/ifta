# statistic/urls.py
from django.urls import path

from .views import (
    DispatcherSheetRowListAPIView,
    WeeklyDayDataByWeekSummaryAPIView,
    WeeklyDayDataListView,
)

urlpatterns = [
    path("weekly-statistic/", WeeklyDayDataListView.as_view(), name="weekly-data-list"),
    path("dispatchers/", DispatcherSheetRowListAPIView.as_view(), name="dispatcher-list"),
    path(
        "weekly-by-week/",
        WeeklyDayDataByWeekSummaryAPIView.as_view(),
        name="weekly-daydata-by-week",
    ),
]
