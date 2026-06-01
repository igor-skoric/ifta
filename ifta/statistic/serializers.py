# statistic/serializers.py
from rest_framework import serializers

from .models import WeeklyDayData, DispatcherSheetRow


class WeeklyDayDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyDayData
        fields = [
            "year",
            "iso_week",
            "day",
            "gross",
            "cut",
            "miles",
            "rate_per_mile",
            "updated_at",
        ]


class DispatcherSheetRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatcherSheetRow
        fields = [
            "id",
            "year",
            "iso_week",
            "dispatcher",
            "gross",
            "cut",
            "miles",
            "rpm",
            "gpu",
            "drpm",
            "imported_at",
            "updated_at",
        ]
