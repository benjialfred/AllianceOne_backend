from django.urls import path
from .views import SchoolCardPdfView, ClassSchoolCardPdfView

urlpatterns = [
    path('cards/student/<int:student_id>/', SchoolCardPdfView.as_view(), name='student-card'),
    path('cards/class/<int:class_id>/', ClassSchoolCardPdfView.as_view(), name='class-card'),
]
