from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

from platform_services.education.students.models import Student, Attendance
from platform_services.education.teachers.models import Teacher
from platform_services.education.classes.models import SchoolClass, AcademicEvent
from platform_services.education.finance.models import TuitionProfile, Payment
from platform_services.education.grades.models import Grade
from django.db.models.functions import Coalesce
from django.db.models import DecimalField, F

class DashboardKPIView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        
        # 1. Students & Classes
        total_students = Student.objects.filter(is_active=False).count() if hasattr(Student, 'is_active') else Student.objects.filter(is_archived=False).count()
        total_teachers = Teacher.objects.count()
        total_classes = SchoolClass.objects.count()
        
        # 2. Attendance (dummy calculation if not fully populated)
        absences_today = Attendance.objects.filter(date=today, is_absent=True).count() if hasattr(Attendance, 'is_absent') else Attendance.objects.filter(date=today, status='absent').count()
        present_today = total_students - absences_today if total_students > absences_today else 0
        
        # 3. Finance
        payments_this_month = Payment.objects.filter(date__gte=first_day_of_month).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate real unpaid fees
        total_tuition = TuitionProfile.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        total_all_payments = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
        unpaid_fees = max(0, total_tuition - total_all_payments)
        
        # 4. Events / Academics
        upcoming_exams = AcademicEvent.objects.filter(start_date__gte=today).count()
        new_enrollments = Student.objects.filter(created_at__gte=today - timedelta(days=30)).count()

        return Response({
            "total_students": total_students,
            "present_today": present_today,
            "absent_today": absences_today,
            "total_teachers": total_teachers,
            "total_classes": total_classes,
            "monthly_revenue": payments_this_month,
            "unpaid_fees": unpaid_fees,
            "upcoming_exams": upcoming_exams,
            "new_enrollments": new_enrollments,
        })

class DashboardIntelligenceView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        alerts = []
        
        # 1. Unpaid fees alert
        tuition_profiles = TuitionProfile.objects.annotate(
            paid=Coalesce(Sum('payments__amount'), 0, output_field=DecimalField())
        )
        unpaid_count = tuition_profiles.filter(total_amount__gt=F('paid')).count()

        if unpaid_count > 0:
            alerts.append({
                "id": "unpaid_fees",
                "type": "warning",
                "title": "Frais impayés",
                "message": f"{unpaid_count} élève(s) ont des frais de scolarité en retard."
            })
            
        # 2. Overloaded classes
        # Safe to remove since capacity isn't tracked yet
        pass
        
        # 3. Upcoming Events
        today = timezone.now().date()
        upcoming = AcademicEvent.objects.filter(start_date__gte=today, start_date__lte=today + timedelta(days=7))
        for ev in upcoming:
            alerts.append({
                "id": f"event_{ev.id}",
                "type": "info",
                "title": ev.title,
                "message": f"Prévu pour le {ev.start_date.strftime('%d/%m/%Y')}."
            })
            
        return Response({"alerts": alerts})

class DashboardTimelineView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        activities = []
        
        # 1. Recent enrollments
        recent_students = Student.objects.order_by('-created_at')[:3]
        for s in recent_students:
            activities.append({
                "id": f"student_{s.id}",
                "timestamp": s.created_at,
                "type": "enrollment",
                "message": f"Nouvel élève inscrit: {s.first_name} {s.last_name}"
            })
            
        # 2. Recent payments
        recent_payments = Payment.objects.order_by('-created_at')[:3]
        for p in recent_payments:
            activities.append({
                "id": f"payment_{p.id}",
                "timestamp": p.created_at,
                "type": "payment",
                "message": f"Paiement confirmé de {p.amount} CFA (Reçu: {p.receipt_number or 'N/A'})"
            })
            
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return Response({"activities": activities})
