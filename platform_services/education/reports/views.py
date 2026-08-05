from platform_services.identity.mixins import TenantQuerySetMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from platform_services.education.students.models import Student
from platform_services.education.classes.models import AcademicYear, SchoolClass
from services.pdf_documents import PdfDocumentService


class BulletinPdfView(APIView):

    def get(self, request, student_id: int):
        academic_year_id = request.query_params.get('academic_year_id')
        sequence = request.query_params.get('sequence', 'seq1')
        student = get_object_or_404(Student.objects.select_related('school_class'), pk=student_id)
        academic_year = (
            get_object_or_404(AcademicYear, pk=academic_year_id)
            if academic_year_id
            else AcademicYear.objects.filter(is_active=True).first()
        )

        if academic_year is None:
            return HttpResponse('Aucune annee academique active', status=404)

        pdf_bytes = PdfDocumentService.build_bulletin(student, academic_year, sequence)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="bulletin-{student.matricule}-{sequence}.pdf"'
        return response


class ClassBulletinPdfView(APIView):

    def get(self, request, class_id: int):
        academic_year_id = request.query_params.get('academic_year_id')
        sequence = request.query_params.get('sequence', 'seq1')
        school_class = get_object_or_404(SchoolClass, pk=class_id)
        academic_year = (
            get_object_or_404(AcademicYear, pk=academic_year_id)
            if academic_year_id
            else AcademicYear.objects.filter(is_active=True).first()
        )

        if academic_year is None:
            return HttpResponse('Aucune annee academique active', status=404)

        pdf_bytes = PdfDocumentService.build_class_bulletins(school_class, academic_year, sequence)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="bulletins-{school_class.name}-{sequence}.pdf"'
        return response


class SchoolCardPdfView(APIView):

    def get(self, request, student_id: int):
        academic_year_id = request.query_params.get('academic_year_id')
        student = get_object_or_404(Student.objects.select_related('school_class'), pk=student_id)
        academic_year = (
            get_object_or_404(AcademicYear, pk=academic_year_id)
            if academic_year_id
            else AcademicYear.objects.filter(is_active=True).first()
        )

        if academic_year is None:
            return HttpResponse('Aucune annee academique active', status=404)

        pdf_bytes = PdfDocumentService.build_school_card(student, academic_year)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="carte-{student.matricule}.pdf"'
        return response
