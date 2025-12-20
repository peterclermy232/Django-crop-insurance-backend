# ============================================
# insurance/views/advisory.py
# ============================================
from datetime import datetime, timedelta
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Count, Avg, Max, Min

from insurance.models import Advisory, WeatherData, Farmer
from insurance.serializers import AdvisorySerializer, WeatherDataSerializer


class AdvisoryViewSet(viewsets.ModelViewSet):
    queryset = Advisory.objects.all()
    serializer_class = AdvisorySerializer

    @action(detail=False, methods=['post'])
    def send_advisory(self, request):
        """Send advisory message"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            advisory = serializer.save()

            if advisory.send_now:
                advisory.status = 'SENT'
                advisory.sent_date_time = timezone.now()
            else:
                advisory.status = 'SCHEDULED'

            advisory.save()

            return Response(
                self.get_serializer(advisory).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def estimate_recipients(self, request):
        """Estimate number of recipients for advisory"""
        province = request.data.get('province')
        district = request.data.get('district')
        sector = request.data.get('sector')
        gender = request.data.get('gender')

        farmers = Farmer.objects.all()

        if province:
            farmers = farmers.filter(farms__location_province=province)
        if district:
            farmers = farmers.filter(farms__location_district=district)
        if sector:
            farmers = farmers.filter(farms__location_sector=sector)
        if gender and gender != 'All':
            farmers = farmers.filter(gender=gender)

        count = farmers.distinct().count()

        return Response({'count': count})


class WeatherDataViewSet(viewsets.ModelViewSet):
    """ViewSet for managing weather data (historical and forecast)"""
    queryset = WeatherData.objects.all()
    serializer_class = WeatherDataSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by data type (HISTORICAL or FORECAST)
        data_type = self.request.query_params.get('type')
        if data_type:
            queryset = queryset.filter(data_type=data_type.upper())

        # Filter by location
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(recorded_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_at__lte=end_date)

        return queryset.order_by('-recorded_at')

    def create(self, request, *args, **kwargs):
        """Create new weather data entry"""
        data = request.data.copy()
        if 'data_type' in data:
            data['data_type'] = data['data_type'].upper()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        """Update weather data entry"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        data = request.data.copy()
        if 'data_type' in data:
            data['data_type'] = data['data_type'].upper()

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get weather data statistics"""
        data_type = request.query_params.get('type', 'HISTORICAL')
        location = request.query_params.get('location')

        queryset = self.get_queryset().filter(data_type=data_type.upper())
        if location:
            queryset = queryset.filter(location=location)

        stats = queryset.aggregate(
            total_records=Count('weather_id'),
            avg_value=Avg('value'),
            max_value=Max('value'),
            min_value=Min('value'),
        )

        # Get locations breakdown
        locations = queryset.values('location').annotate(
            count=Count('weather_id'),
            avg_value=Avg('value')
        ).order_by('-count')

        return Response({
            'statistics': stats,
            'by_location': list(locations),
            'data_type': data_type
        })

    @action(detail=False, methods=['get'])
    def historical(self, request):
        """Get only historical weather data"""
        queryset = self.get_queryset().filter(data_type='HISTORICAL')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def forecast(self, request):
        """Get only forecast weather data"""
        queryset = self.get_queryset().filter(data_type='FORECAST')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def compare(self, request):
        """Compare historical and forecast data"""
        location = request.query_params.get('location')
        if not location:
            return Response(
                {'error': 'Location parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get historical data
        historical = WeatherData.objects.filter(
            location=location,
            data_type='HISTORICAL'
        ).aggregate(
            avg_value=Avg('value'),
            max_value=Max('value'),
            min_value=Min('value'),
            count=Count('weather_id')
        )

        # Get forecast data
        forecast = WeatherData.objects.filter(
            location=location,
            data_type='FORECAST'
        ).aggregate(
            avg_value=Avg('value'),
            max_value=Max('value'),
            min_value=Min('value'),
            count=Count('weather_id')
        )

        return Response({
            'location': location,
            'historical': historical,
            'forecast': forecast
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent weather data (last 7 days)"""
        data_type = request.query_params.get('type')
        days = int(request.query_params.get('days', 7))

        since = datetime.now() - timedelta(days=days)
        queryset = self.get_queryset().filter(recorded_at__gte=since)

        if data_type:
            queryset = queryset.filter(data_type=data_type.upper())

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """Bulk delete weather data by IDs"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': 'No IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count = WeatherData.objects.filter(
            weather_id__in=ids
        ).delete()[0]

        return Response({
            'message': f'Successfully deleted {deleted_count} records',
            'deleted_count': deleted_count
        })

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create weather data entries"""
        data_list = request.data.get('data', [])
        if not data_list:
            return Response(
                {'error': 'No data provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure all data_types are uppercase
        for item in data_list:
            if 'data_type' in item:
                item['data_type'] = item['data_type'].upper()

        serializer = self.get_serializer(data=data_list, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response({
            'message': f'Successfully created {len(serializer.data)} records',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)


