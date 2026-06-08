from django.urls import path
from django.views.generic import RedirectView

from .views import statistic, statistic2, statistic3, tv_rotator, weekly_analytics

app_name = "statistics"

urlpatterns = [
    path("", weekly_analytics, name="home"),
    # Short paths for TV browsers (bookmark: /statistics/1/ …)
    path("1/", statistic, name="dispatchers_grid"),
    path("2/", statistic2, name="dispatchers_ranking"),
    path("3/", statistic3, name="weather"),
    path("weekly-analytics/", weekly_analytics, name="weekly_analytics"),
    # Legacy URLs → short paths
    path(
        "dispatchers-grid/",
        RedirectView.as_view(url="/statistics/1/", permanent=True),
    ),
    path(
        "dispatchers-ranking/",
        RedirectView.as_view(url="/statistics/2/", permanent=True),
    ),
    path("tv-rotator/", tv_rotator, name="tv_rotator"),
]
