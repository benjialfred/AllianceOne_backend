import csv
from decimal import Decimal
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from platform_services.identity.mixins import TenantQuerySetMixin

from .models import (
    FinancialAccount, FinancialCategory, Transaction,
    Budget, Invoice, InvoiceItem,
    TontineGroup, TontineMember, TontineRound,
    TontineContribution, TontinePayout
)
from .serializers import (
    FinancialAccountSerializer, FinancialCategorySerializer,
    TransactionSerializer, BudgetSerializer, InvoiceSerializer,
    InvoiceItemSerializer,
    TontineGroupSerializer, TontineMemberSerializer,
    TontineRoundSerializer, TontineContributionSerializer,
    TontinePayoutSerializer
)
from .services import FinanceService


class FinancialAccountViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = FinancialAccount.objects.all()
    serializer_class = FinancialAccountSerializer
    search_fields = ['name', 'account_number', 'institution_name']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        initial_balance = serializer.validated_data.get('initial_balance', Decimal('0.00'))
        serializer.save(organization=tenant, current_balance=initial_balance)

    @action(detail=True, methods=['post'])
    def recalculate_balance(self, request, pk=None):
        account = self.get_object()
        new_balance = FinanceService.recalculate_account_balance(account)
        return Response({
            'message': 'Solde recalculé avec succès.',
            'current_balance': float(new_balance)
        })

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        account = self.get_object()
        txs = Transaction.objects.filter(
            organization=request.tenant,
            account=account
        ).order_by('-date', '-created_at')[:50]
        serializer = TransactionSerializer(txs, many=True)
        return Response(serializer.data)


class FinancialCategoryViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = FinancialCategory.objects.all()
    serializer_class = FinancialCategorySerializer
    search_fields = ['name', 'code']

    @action(detail=False, methods=['post'])
    def generate_defaults(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Organisation requise.'}, status=status.HTTP_400_BAD_REQUEST)
        
        created = FinanceService.generate_default_categories(tenant)
        serializer = FinancialCategorySerializer(created, many=True)
        return Response({
            'message': f'{len(created)} catégories standards générées avec succès.',
            'categories': serializer.data
        }, status=status.HTTP_201_CREATED)


class TransactionViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related('account', 'destination_account', 'category').all()
    serializer_class = TransactionSerializer
    search_fields = ['title', 'reference_number', 'payee_payer', 'notes']

    def get_queryset(self):
        qs = super().get_queryset()
        tx_type = self.request.query_params.get('type')
        account_id = self.request.query_params.get('account')
        category_id = self.request.query_params.get('category')
        currency = self.request.query_params.get('currency')
        tx_status = self.request.query_params.get('status')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if tx_type:
            qs = qs.filter(transaction_type=tx_type)
        if account_id:
            qs = qs.filter(account_id=account_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if currency:
            qs = qs.filter(currency=currency)
        if tx_status:
            qs = qs.filter(status=tx_status)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        return qs

    def create(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Organisation requise.'}, status=status.HTTP_400_BAD_REQUEST)
        
        tx = FinanceService.record_transaction(tenant, request.data, user=request.user)
        serializer = TransactionSerializer(tx)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        FinanceService.rollback_transaction_impact(instance)
        instance.delete()

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        qs = self.get_queryset()
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="transactions_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Libellé', 'Compte', 'Catégorie', 'Montant', 'Devise', 'Tiers', 'Moyen Paiement', 'Statut', 'Référence'])
        
        for tx in qs:
            writer.writerow([
                tx.date,
                tx.get_transaction_type_display(),
                tx.title,
                tx.account.name if tx.account else '',
                tx.category.name if tx.category else '',
                tx.amount,
                tx.currency,
                tx.payee_payer or '',
                tx.get_payment_method_display(),
                tx.get_status_display(),
                tx.reference_number or ''
            ])
        
        return response


class BudgetViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Budget.objects.select_related('category').all()
    serializer_class = BudgetSerializer
    search_fields = ['name', 'category__name']


class InvoiceViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.prefetch_related('items').all()
    serializer_class = InvoiceSerializer
    search_fields = ['invoice_number', 'partner_name', 'partner_email']

    def get_queryset(self):
        qs = super().get_queryset()
        inv_type = self.request.query_params.get('type')
        inv_status = self.request.query_params.get('status')
        currency = self.request.query_params.get('currency')

        if inv_type:
            qs = qs.filter(invoice_type=inv_type)
        if inv_status:
            qs = qs.filter(status=inv_status)
        if currency:
            qs = qs.filter(currency=currency)

        return qs

    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        invoice = self.get_object()
        account_id = request.data.get('account_id')
        payment_amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'TRANSFER')
        reference = request.data.get('reference', '')
        date = request.data.get('date')

        if not account_id or not payment_amount:
            return Response({'error': 'Compte et montant requis.'}, status=status.HTTP_400_BAD_REQUEST)

        tx = FinanceService.record_invoice_payment(
            invoice=invoice,
            account_id=account_id,
            payment_amount=payment_amount,
            payment_method=payment_method,
            reference=reference,
            date=date,
            user=request.user
        )

        inv_serializer = InvoiceSerializer(invoice)
        tx_serializer = TransactionSerializer(tx)

        return Response({
            'message': 'Règlement enregistré et transaction comptabilisée avec succès.',
            'invoice': inv_serializer.data,
            'transaction': tx_serializer.data
        })

    @action(detail=True, methods=['post'])
    def mark_status(self, request, pk=None):
        invoice = self.get_object()
        new_status = request.data.get('status')
        if new_status not in dict(invoice._meta.get_field('status').choices):
            return Response({'error': 'Statut invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        invoice.status = new_status
        invoice.save(update_fields=['status'])
        return Response(InvoiceSerializer(invoice).data)


# ==============================================================================
# TONTINE VIEWSETS
# ==============================================================================

class TontineGroupViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TontineGroup.objects.prefetch_related('members', 'rounds').all()
    serializer_class = TontineGroupSerializer
    search_fields = ['name', 'description']

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(organization=tenant, created_by=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=True, methods=['post'])
    def generate_rounds(self, request, pk=None):
        tontine = self.get_object()
        rounds = FinanceService.generate_tontine_rounds(tontine)
        serializer = TontineRoundSerializer(rounds, many=True)
        return Response({
            'message': f'{len(rounds)} tours générés avec succès pour la tontine.',
            'rounds': serializer.data
        }, status=status.HTTP_200_OK)


class TontineMemberViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TontineMember.objects.all()
    serializer_class = TontineMemberSerializer
    search_fields = ['full_name', 'phone', 'email']

    def get_queryset(self):
        qs = super().get_queryset()
        tontine_id = self.request.query_params.get('tontine')
        if tontine_id:
            qs = qs.filter(tontine_id=tontine_id)
        return qs


class TontineRoundViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TontineRound.objects.select_related('beneficiary').prefetch_related('contributions').all()
    serializer_class = TontineRoundSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        tontine_id = self.request.query_params.get('tontine')
        if tontine_id:
            qs = qs.filter(tontine_id=tontine_id)
        return qs

    @action(detail=True, methods=['post'])
    def record_payout(self, request, pk=None):
        round_obj = self.get_object()
        data = request.data.copy()
        data['round'] = round_obj.id
        data['tontine'] = round_obj.tontine_id
        if not data.get('beneficiary'):
            data['beneficiary'] = round_obj.beneficiary_id

        payout = FinanceService.record_tontine_payout(request.tenant, data, user=request.user)
        return Response(TontinePayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class TontineContributionViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TontineContribution.objects.select_related('member', 'round').all()
    serializer_class = TontineContributionSerializer
    search_fields = ['member__full_name', 'reference']

    def get_queryset(self):
        qs = super().get_queryset()
        tontine_id = self.request.query_params.get('tontine')
        round_id = self.request.query_params.get('round')
        member_id = self.request.query_params.get('member')
        if tontine_id:
            qs = qs.filter(tontine_id=tontine_id)
        if round_id:
            qs = qs.filter(round_id=round_id)
        if member_id:
            qs = qs.filter(member_id=member_id)
        return qs

    def create(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Organisation requise.'}, status=status.HTTP_400_BAD_REQUEST)
        
        contribution = FinanceService.record_tontine_contribution(tenant, request.data, user=request.user)
        return Response(TontineContributionSerializer(contribution).data, status=status.HTTP_201_CREATED)


class TontinePayoutViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = TontinePayout.objects.select_related('beneficiary', 'round').all()
    serializer_class = TontinePayoutSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        tontine_id = self.request.query_params.get('tontine')
        if tontine_id:
            qs = qs.filter(tontine_id=tontine_id)
        return qs

