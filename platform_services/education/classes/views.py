from platform_services.identity.mixins import TenantQuerySetMixin
from rest_framework import viewsets
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response


from .models import AcademicYear, SchoolClass, AcademicEvent, Level, Section, SeriesGroup, Series
from .serializers import AcademicYearSerializer, SchoolClassSerializer, AcademicEventSerializer, LevelSerializer, SectionSerializer, SeriesGroupSerializer, SeriesSerializer
from .services import promote_students, PromotionEngine

class LevelViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Level.objects.all()
    serializer_class = LevelSerializer

class SectionViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer

class SeriesGroupViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = SeriesGroup.objects.all()
    serializer_class = SeriesGroupSerializer

class SeriesViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Series.objects.select_related('group').all()
    serializer_class = SeriesSerializer
class AcademicYearViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer

class SchoolClassViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = SchoolClass.objects.select_related('academic_year', 'head_teacher').all()
    serializer_class = SchoolClassSerializer

    @action(detail=False, methods=['post'])
    def process_promotions(self, request):
        source_academic_year_id = request.data.get('source_academic_year_id')
        target_academic_year_id = request.data.get('target_academic_year_id')
        decisions = request.data.get('decisions', [])

        if not all([source_academic_year_id, target_academic_year_id, decisions]):
            return Response({'error': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            results = PromotionEngine.process_promotions(
                source_academic_year_id, 
                target_academic_year_id, 
                decisions, 
                user=request.user if request.user.is_authenticated else None
            )
            return Response(results)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AcademicEventViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = AcademicEvent.objects.select_related('academic_year', 'created_by').all()
    serializer_class = AcademicEventSerializer
    filterset_fields = ['academic_year']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

