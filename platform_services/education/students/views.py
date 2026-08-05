from platform_services.identity.mixins import TenantQuerySetMixin
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.files.storage import default_storage
import openpyxl
from datetime import datetime


from .models import Student, Attendance, Enrollment
from .serializers import StudentSerializer, AttendanceSerializer, EnrollmentSerializer

class EnrollmentViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    filterset_fields = ['student', 'academic_year', 'school_class', 'decision']


class StudentViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filterset_fields = ['lifecycle_status', 'is_archived']

    def get_queryset(self):
        queryset = Student.objects.prefetch_related('enrollments', 'enrollments__school_class').all()
        is_archived = self.request.query_params.get('is_archived', 'false')
        if is_archived.lower() == 'true':
            queryset = queryset.filter(is_archived=True)
        else:
            queryset = queryset.filter(is_archived=False)
            
        school_class = self.request.query_params.get('school_class')
        if school_class:
            queryset = queryset.filter(enrollments__school_class_id=school_class).distinct()
            
        return queryset

    def perform_destroy(self, instance):
        instance.is_archived = True
        instance.save()

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        student = self.get_object()
        student.is_archived = False
        student.save()
        return Response({'status': 'student restored'})
    @action(detail=False, methods=['post'])
    def import_excel(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'Aucun fichier fourni.'}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        if not file.name.endswith('.xlsx'):
            return Response({'error': 'Le fichier doit être au format .xlsx'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active
            
            created = 0
            errors = []
            
            # On suppose que la première ligne contient les en-têtes:
            # Nom | Prénom | Sexe | Date de naissance (YYYY-MM-DD) | Lieu de naissance | Classe ID | Nom Parent | Téléphone Parent
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if not row[0]: continue # Ligne vide
                
                try:
                    last_name = str(row[0])
                    first_name = str(row[1]) if row[1] else ''
                    sex = str(row[2]) if row[2] else 'M'
                    dob_raw = row[3]
                    
                    if isinstance(dob_raw, datetime):
                        dob = dob_raw.date()
                    else:
                        try:
                            dob = datetime.strptime(str(dob_raw), "%Y-%m-%d").date()
                        except:
                            dob = datetime.strptime("2000-01-01", "%Y-%m-%d").date()
                            
                    place_of_birth = str(row[4]) if row[4] else 'Inconnu'
                    school_class_id = int(row[5]) if row[5] else None
                    parent_name = str(row[6]) if row[6] else 'Inconnu'
                    parent_phone = str(row[7]) if row[7] else ''
                    
                    if school_class_id:
                        from platform_services.education.classes.models import SchoolClass
                        school_class = SchoolClass.objects.filter(id=school_class_id).first()
                        if not school_class:
                            errors.append(f"Ligne {row_idx}: Classe ID {school_class_id} introuvable.")
                            continue
                            
                    student = Student(
                        last_name=last_name,
                        first_name=first_name,
                        sex=sex,
                        date_of_birth=dob,
                        place_of_birth=place_of_birth,
                        school_class_id=school_class_id,
                        parent_name=parent_name,
                        parent_phone=parent_phone
                    )
                    student.save()
                    created += 1
                except Exception as e:
                    errors.append(f"Ligne {row_idx}: Erreur lors de l'intégration ({str(e)})")
                    
            return Response({'message': f'{created} élèves importés avec succès.', 'errors': errors})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AttendanceViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    filterset_fields = ['student', 'date', 'academic_year', 'sequence']
    
    @action(detail=False, methods=['post'])
    def batch(self, request):
        attendances_data = request.data.get('attendances', [])
        # expects: [{'student': ID, 'date': 'YYYY-MM-DD', 'academic_year': ID, 'sequence': str, 'is_absent': bool}]
        
        if not attendances_data:
            return Response({'error': 'No data provided.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check CalendarEngine for the first date in batch (assuming batch is usually for same date)
        sample_date = attendances_data[0].get('date')
        if sample_date:
            from platform_services.education.classes.services import CalendarEngine
            if CalendarEngine.is_attendance_suspended(sample_date, organization_id=request.user.organization_id if hasattr(request.user, 'organization_id') else None):
                return Response({'error': 'L\'appel est suspendu pour cette date (jour férié ou événement spécial).'}, status=status.HTTP_400_BAD_REQUEST)
        
        created = 0
        updated = 0
        
        for a_data in attendances_data:
            student_id = a_data.get('student')
            date = a_data.get('date')
            sequence = a_data.get('sequence')
            academic_year_id = a_data.get('academic_year')
            is_absent = a_data.get('is_absent', False)
            
            if not all([student_id, date, sequence, academic_year_id]):
                continue
                
            att_obj, is_new = Attendance.objects.get_or_create(
                student_id=student_id,
                date=date,
                sequence=sequence,
                defaults={
                    'academic_year_id': academic_year_id,
                    'is_absent': is_absent,
                    'organization_id': request.user.organization_id if hasattr(request.user, 'organization_id') else None
                }
            )
            
            if not is_new:
                att_obj.is_absent = is_absent
                att_obj.save()
                updated += 1
            else:
                created += 1
                
        return Response({'message': 'Appel enregistré.', 'created': created, 'updated': updated})

