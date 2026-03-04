# statistic/serializers.py
from rest_framework import serializers
from .models import WeeklyDriverData, WeeklyDayData, DispatcherSheetRow


class WeeklyDriverDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyDriverData
        fields = [
            "driver", "dispatch", "miles", "avg", "gross", "driver_gross",
            "cut", "salary", "truck", "profit_loss", "mpg", "idle_time", "idle_percent"
        ]


class WeeklyDriverDataResponseSerializer(serializers.Serializer):
    total_profit_loss = serializers.SerializerMethodField()
    data = WeeklyDriverDataSerializer(many=True)

    def get_total_profit_loss(self, obj):
        # suma svih profit_loss u bazi
        return WeeklyDriverData.total_profit_loss()


class WeeklyDayDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyDayData
        fields = ['day', 'gross', 'cut', 'miles', 'rate_per_mile']


class DispatcherSheetRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatcherSheetRow
        fields = [
            "id",
            "dispatcher",
            "gross",
            "cut",
            "miles",
            "rpm",
            "gpu",
            "imported_at",
        ]