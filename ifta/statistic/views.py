# statistic/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from .models import WeeklyDriverData, WeeklyDayData
from .serializers import WeeklyDriverDataSerializer, WeeklyDayDataSerializer, WeeklyDriverDataResponseSerializer
from rest_framework.decorators import api_view


@api_view(['GET'])
def WeeklyDriverDataAPI(request):
    queryset = WeeklyDriverData.objects.all()
    serializer = WeeklyDriverDataSerializer(queryset, many=True)

    response_serializer = WeeklyDriverDataResponseSerializer({
        "profit_total": WeeklyDriverData.total_profit_loss(),
        "data": serializer.data
    })

    return Response(response_serializer.data)


class WeeklyDayDataListView(generics.ListAPIView):
    queryset = WeeklyDayData.objects.all().order_by('day')
    serializer_class = WeeklyDayDataSerializer