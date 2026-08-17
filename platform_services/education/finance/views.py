from platform_services.identity.mixins import TenantQuerySetMixin
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import TuitionProfile, Payment
from .serializers import TuitionProfileSerializer, PaymentSerializer

from reportlab.lib.pagesizes import A5, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from django.shortcuts import get_object_or_404
from django.views import View
from platform_services.education.finance.utils import int_to_words_fr
from rest_framework.decorators import action
from rest_framework.response import Response

class TuitionProfileViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TuitionProfile.objects.all()
    serializer_class = TuitionProfileSerializer
    filterset_fields = ['student', 'academic_year', 'student__school_class']

    @action(detail=True, methods=['post'])
    def send_reminder(self, request, pk=None):
        profile = self.get_object()
        # Simulation d'envoi de SMS/Email
        import time
        time.sleep(1) # simulate network call
        if profile.remaining_amount <= 0:
            return Response({"error": "L'élève est déjà en règle."}, status=400)
        return Response({"success": f"Relance envoyée avec succès pour {profile.student} (Reste: {profile.remaining_amount} FCFA)."})

class PaymentViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filterset_fields = ['tuition_profile', 'tuition_profile__student', 'tuition_profile__academic_year']

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

class ReceiptPdfView(View):
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        
        buffer = io.BytesIO()
        # Format A5 Paysage
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A5), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Titre
        title_style = ParagraphStyle(
            'ReceiptTitle', 
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f2937'),
            alignment=1 # Center
        )
        
        school_name = "ALLIANCE ONE"
        if hasattr(request, 'tenant') and request.tenant:
            school_name = request.tenant.name.upper()

        elements.append(Paragraph(f"<b>{school_name}</b>", title_style))
        elements.append(Paragraph("REÇU DE PAIEMENT", ParagraphStyle('Sub', parent=title_style, fontSize=12, textColor=colors.HexColor('#4b5563'))))
        elements.append(Spacer(1, 0.5 * cm))
        
        # Informations
        info_data = [
            ["N° Reçu:", payment.receipt_number, "Date:", payment.date.strftime("%d/%m/%Y %H:%M")],
            ["Élève:", f"{payment.tuition_profile.student.first_name} {payment.tuition_profile.student.last_name}", "Matricule:", payment.tuition_profile.student.matricule or "N/A"],
            ["Classe:", payment.tuition_profile.student.school_class.name if payment.tuition_profile.student.school_class else "N/A", "Année:", payment.tuition_profile.academic_year.label],
            ["Méthode:", payment.get_payment_method_display(), "Référence:", payment.reference_number_trans or "-"],
        ]
        
        info_table = Table(info_data, colWidths=[2.5*cm, 7*cm, 2.5*cm, 4*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 1 * cm))
        
        # Montant
        amount_style = ParagraphStyle(
            'Amount', 
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#059669'),
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph(f"Montant Payé : {int(payment.amount):,} FCFA".replace(',', ' '), amount_style))
        
        # Montant en lettres (Si la fonction int_to_words_fr échoue, on fallback)
        try:
            amount_words = int_to_words_fr(int(payment.amount))
        except:
            amount_words = "..........................................................."
            
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph(f"<i>Arrêté le présent reçu à la somme de : <b>{amount_words} Francs CFA</b>.</i>", styles['Normal']))
        
        elements.append(Spacer(1, 1 * cm))
        
        # Signatures
        sig_data = [
            ["La Caisse", "Le Payeur (Parent/Élève)"]
        ]
        sig_table = Table(sig_data, colWidths=[8*cm, 8*cm])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(sig_table)
        
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Recu_{payment.receipt_number}.pdf"'
        return response
