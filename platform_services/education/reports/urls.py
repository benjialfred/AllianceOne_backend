from django.urls import path
from .views import BulletinPdfView, ClassBulletinPdfView

urlpatterns = [
    path('reports/bulletins/student/<int:student_id>/', BulletinPdfView.as_view(), name='student-bulletin'),
    path('reports/bulletins/class/<int:class_id>/', ClassBulletinPdfView.as_view(), name='class-bulletin'),
]
