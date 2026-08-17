from django.urls import path, include
from rest_framework.routers import DefaultRouter

from platform_services.education.students.views import StudentViewSet, AttendanceViewSet, EnrollmentViewSet
from platform_services.education.classes.views import SchoolClassViewSet, AcademicYearViewSet, AcademicEventViewSet, LevelViewSet, SectionViewSet, SeriesGroupViewSet, SeriesViewSet
from platform_services.education.teachers.views import TeacherViewSet
from platform_services.education.subjects.views import SubjectViewSet
from platform_services.education.grades.views import GradeViewSet, SequenceValidationViewSet, GradeHistoryViewSet
from platform_services.education.finance.views import TuitionProfileViewSet, PaymentViewSet, ReceiptPdfView

router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'attendances', AttendanceViewSet, basename='attendance')
router.register(r'classes', SchoolClassViewSet, basename='schoolclass')
router.register(r'levels', LevelViewSet, basename='level')
router.register(r'sections', SectionViewSet, basename='section')
router.register(r'series-groups', SeriesGroupViewSet, basename='seriesgroup')
router.register(r'series', SeriesViewSet, basename='series')
router.register(r'academic-years', AcademicYearViewSet, basename='academicyear')
router.register(r'academic-events', AcademicEventViewSet, basename='academicevent')
router.register(r'teachers', TeacherViewSet, basename='teacher')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'grades', GradeViewSet, basename='grade')
router.register(r'sequence-validations', SequenceValidationViewSet, basename='sequencevalidation')
router.register(r'grade-history', GradeHistoryViewSet, basename='gradehistory')
router.register(r'tuition-profiles', TuitionProfileViewSet, basename='tuitionprofile')
router.register(r'payments', PaymentViewSet, basename='payment')

from platform_services.education.api.dashboard_views import DashboardKPIView, DashboardIntelligenceView, DashboardTimelineView

urlpatterns = [
    path('', include(router.urls)),
    path('', include('platform_services.education.reports.urls')),
    path('', include('platform_services.education.cards.urls')),
    path('finance/receipt/<int:payment_id>/', ReceiptPdfView.as_view(), name='finance-receipt'),
    path('dashboard-stats/kpis/', DashboardKPIView.as_view(), name='dashboard-kpis'),
    path('dashboard-stats/intelligence/', DashboardIntelligenceView.as_view(), name='dashboard-intelligence'),
    path('dashboard-stats/timeline/', DashboardTimelineView.as_view(), name='dashboard-timeline'),
]
