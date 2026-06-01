# statistic/views.py
from django.db.models import Case, IntegerField, Sum, Value, When
from rest_framework import generics
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WeeklyDayData, DispatcherSheetRow
from .permissions import StatisticsAnalyticsPermission, StatisticsReadPermission
from .serializers import WeeklyDayDataSerializer, DispatcherSheetRowSerializer
from .week_scope import current_iso_year_week

_DAY_ORDER = {
    "Mon": 1,
    "Tue": 2,
    "Wed": 3,
    "Thu": 4,
    "Fri": 5,
    "Sat": 6,
    "Sun": 7,
    "TOTALS": 99,
}


class WeeklyDayDataListView(generics.ListAPIView):
    serializer_class = WeeklyDayDataSerializer
    permission_classes = [StatisticsReadPermission]

    def get_queryset(self):
        y, w = current_iso_year_week()
        order = Case(
            *[
                When(day=k, then=Value(v))
                for k, v in _DAY_ORDER.items()
            ],
            default=Value(100),
            output_field=IntegerField(),
        )
        return (
            WeeklyDayData.objects.filter(year=y, iso_week=w)
            .annotate(_day_sort=order)
            .order_by("_day_sort")
        )


class DispatcherSheetRowListAPIView(ListAPIView):
    serializer_class = DispatcherSheetRowSerializer
    permission_classes = [StatisticsReadPermission]

    def get_queryset(self):
        y, w = current_iso_year_week()
        return DispatcherSheetRow.objects.filter(year=y, iso_week=w).order_by("-rpm")


class WeeklyDayDataByWeekSummaryAPIView(APIView):
    """
    Agregat WeeklyDayData po (ISO godina, nedelja), bez reda TOTALS
    (da se ne dupliraju sume). Za grafikon i tabelu uporedjenja nedelja.
    """

    permission_classes = [StatisticsAnalyticsPermission]

    def get(self, request):
        qs = (
            WeeklyDayData.objects.exclude(day="TOTALS")
            .values("year", "iso_week")
            .annotate(
                total_gross=Sum("gross"),
                total_cut=Sum("cut"),
                total_miles=Sum("miles"),
            )
            .order_by("year", "iso_week")
        )
        year_filter = request.query_params.get("year")
        if year_filter and str(year_filter).isdigit():
            qs = qs.filter(year=int(year_filter))

        rows = []
        for r in qs:
            tg = r["total_gross"] or 0
            tc = r["total_cut"] or 0
            tm = r["total_miles"] or 0
            tg_f = float(tg)
            tm_i = int(tm)
            rpm = (tg_f / float(tm_i)) if tm_i else 0.0
            y, w = r["year"], r["iso_week"]
            rows.append(
                {
                    "year": y,
                    "iso_week": w,
                    "label": f"{y}-W{w:02d}",
                    "total_gross": round(tg_f, 2),
                    "total_cut": round(float(tc), 2),
                    "total_miles": tm_i,
                    "blended_rate_per_mile": round(rpm, 4),
                }
            )
        return Response(rows)
