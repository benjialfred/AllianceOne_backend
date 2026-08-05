from platform_services.identity.mixins import TenantQuerySetMixin
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import TuitionProfile, Payment
from .serializers import TuitionProfileSerializer, PaymentSerializer

class TuitionProfileViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TuitionProfile.objects.all()
    serializer_class = TuitionProfileSerializer
    filterset_fields = ['student', 'academic_year', 'student__school_class']

class PaymentViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filterset_fields = ['tuition_profile', 'tuition_profile__student', 'tuition_profile__academic_year']

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

import io
import os
from django.conf import settings as django_settings
from django.http import HttpResponse
from django.views import View
# from reportlab.lib.pagesizes import A5, landscape
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Frame, PageTemplate
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib import colors
# from reportlab.lib.units import cm
from django.shortcuts import get_object_or_404
# from platform_services.education.core.models import SchoolSettings
from platform_services.education.finance.utils import int_to_words_fr

class ReceiptPdfView(View):
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        from django.http import JsonResponse
        return JsonResponse({"status": "pdf disabled temporarily", "receipt_number": payment.receipt_number})
