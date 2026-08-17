from decimal import Decimal
from rest_framework import serializers
from django.db.models import Sum
from .models import (
    FinancialAccount, FinancialCategory, Transaction,
    Budget, Invoice, InvoiceItem,
    TontineGroup, TontineMember, TontineRound,
    TontineContribution, TontinePayout
)


class FinancialAccountSerializer(serializers.ModelSerializer):
    transactions_count = serializers.SerializerMethodField()
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)

    class Meta:
        model = FinancialAccount
        fields = [
            'id', 'name', 'account_type', 'account_type_display',
            'account_number', 'institution_name', 'currency', 'currency_display',
            'initial_balance', 'current_balance', 'color', 'is_active',
            'is_default', 'description', 'created_at', 'updated_at',
            'transactions_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_transactions_count(self, obj):
        return obj.transactions.count()


class FinancialCategorySerializer(serializers.ModelSerializer):
    category_type_display = serializers.CharField(source='get_category_type_display', read_only=True)
    subcategories = serializers.SerializerMethodField()
    transactions_count = serializers.SerializerMethodField()

    class Meta:
        model = FinancialCategory
        fields = [
            'id', 'name', 'category_type', 'category_type_display',
            'code', 'parent', 'color', 'icon', 'description',
            'subcategories', 'transactions_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return FinancialCategorySerializer(obj.subcategories.all(), many=True).data
        return []

    def get_transactions_count(self, obj):
        return obj.transactions.count()


class TransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_color = serializers.CharField(source='account.color', read_only=True)
    destination_account_name = serializers.CharField(source='destination_account.name', read_only=True, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    category_color = serializers.CharField(source='category.color', read_only=True, allow_null=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True, allow_null=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display',
            'title', 'account', 'account_name', 'account_color',
            'destination_account', 'destination_account_name',
            'category', 'category_name', 'category_color', 'category_icon',
            'amount', 'currency', 'destination_amount', 'exchange_rate',
            'date', 'reference_number', 'payment_method', 'payment_method_display',
            'payee_payer', 'status', 'status_display', 'notes', 'receipt_url',
            'is_reconciled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    spent_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    percentage_used = serializers.SerializerMethodField()
    is_warning = serializers.SerializerMethodField()
    is_exceeded = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'category', 'category_name', 'category_color', 'category_icon',
            'allocated_amount', 'currency', 'period', 'start_date', 'end_date',
            'alert_threshold_percentage', 'is_active', 'notes',
            'spent_amount', 'remaining_amount', 'percentage_used', 'is_warning', 'is_exceeded',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def _get_spent(self, obj):
        spent = Transaction.objects.filter(
            organization=obj.organization,
            category=obj.category,
            transaction_type='EXPENSE',
            status='COMPLETED',
            date__range=[obj.start_date, obj.end_date]
        ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        return spent

    def get_spent_amount(self, obj):
        return float(self._get_spent(obj))

    def get_remaining_amount(self, obj):
        spent = self._get_spent(obj)
        return float(max(Decimal('0.00'), obj.allocated_amount - spent))

    def get_percentage_used(self, obj):
        spent = self._get_spent(obj)
        if obj.allocated_amount > Decimal('0'):
            return round(float((spent / obj.allocated_amount) * 100), 1)
        return 0.0

    def get_is_warning(self, obj):
        pct = self.get_percentage_used(obj)
        return pct >= obj.alert_threshold_percentage

    def get_is_exceeded(self, obj):
        spent = self._get_spent(obj)
        return spent > obj.allocated_amount


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['id']


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    remaining_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    invoice_type_display = serializers.CharField(source='get_invoice_type_display', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_type', 'invoice_type_display', 'invoice_number',
            'partner_name', 'partner_email', 'partner_phone', 'partner_address', 'partner_tax_id',
            'issue_date', 'due_date', 'currency', 'status', 'status_display',
            'subtotal', 'tax_rate', 'tax_amount', 'discount_amount', 'total_amount',
            'paid_amount', 'remaining_due', 'notes', 'terms', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        invoice = Invoice.objects.create(**validated_data)
        
        calculated_subtotal = Decimal('0.00')
        for item_data in items_data:
            item = InvoiceItem.objects.create(
                organization=invoice.organization,
                invoice=invoice,
                **item_data
            )
            calculated_subtotal += item.total_price
        
        if items_data:
            invoice.subtotal = calculated_subtotal
            tax_rate = invoice.tax_rate or Decimal('0.00')
            discount = invoice.discount_amount or Decimal('0.00')
            invoice.tax_amount = (invoice.subtotal * tax_rate) / Decimal('100.00')
            invoice.total_amount = max(Decimal('0.00'), invoice.subtotal + invoice.tax_amount - discount)
            invoice.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])

        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if items_data is not None:
            instance.items.all().delete()
            calculated_subtotal = Decimal('0.00')
            for item_data in items_data:
                item = InvoiceItem.objects.create(
                    organization=instance.organization,
                    invoice=instance,
                    **item_data
                )
                calculated_subtotal += item.total_price
            instance.subtotal = calculated_subtotal
            tax_rate = instance.tax_rate or Decimal('0.00')
            discount = instance.discount_amount or Decimal('0.00')
            instance.tax_amount = (instance.subtotal * tax_rate) / Decimal('100.00')
            instance.total_amount = max(Decimal('0.00'), instance.subtotal + instance.tax_amount - discount)

        instance.save()
        return instance


# ==============================================================================
# TONTINE SERIALIZERS
# ==============================================================================

class TontineMemberSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_contributed = serializers.SerializerMethodField()
    total_received = serializers.SerializerMethodField()

    class Meta:
        model = TontineMember
        fields = [
            'id', 'tontine', 'full_name', 'phone', 'email', 'address',
            'shares_count', 'payout_order', 'expected_payout_date',
            'has_received_payout', 'status', 'status_display', 'notes',
            'total_contributed', 'total_received', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_total_contributed(self, obj):
        tot = obj.contributions.filter(status='PAID').aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        return float(tot)

    def get_total_received(self, obj):
        tot = obj.payouts.aggregate(tot=Sum('net_amount'))['tot'] or Decimal('0.00')
        return float(tot)


class TontineContributionSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    round_number = serializers.IntegerField(source='round.round_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = TontineContribution
        fields = [
            'id', 'tontine', 'round', 'round_number', 'member', 'member_name',
            'amount', 'penalty_paid', 'payment_date', 'payment_method',
            'payment_method_display', 'reference', 'status', 'status_display',
            'transaction', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TontinePayoutSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source='beneficiary.full_name', read_only=True)
    round_number = serializers.IntegerField(source='round.round_number', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = TontinePayout
        fields = [
            'id', 'tontine', 'round', 'round_number', 'beneficiary',
            'beneficiary_name', 'gross_amount', 'deductions', 'net_amount',
            'payout_date', 'payment_method', 'payment_method_display',
            'reference', 'notes', 'transaction', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TontineRoundSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source='beneficiary.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    contributions = TontineContributionSerializer(many=True, read_only=True)
    contributions_count = serializers.SerializerMethodField()
    expected_members_count = serializers.SerializerMethodField()

    class Meta:
        model = TontineRound
        fields = [
            'id', 'tontine', 'round_number', 'due_date', 'beneficiary',
            'beneficiary_name', 'target_amount', 'collected_amount',
            'payout_amount', 'status', 'status_display', 'payout_date',
            'notes', 'contributions', 'contributions_count', 'expected_members_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_contributions_count(self, obj):
        return obj.contributions.filter(status='PAID').count()

    def get_expected_members_count(self, obj):
        return obj.tontine.members.filter(status='ACTIVE').count()


class TontineGroupSerializer(serializers.ModelSerializer):
    tontine_type_display = serializers.CharField(source='get_tontine_type_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True, allow_null=True)
    members_count = serializers.SerializerMethodField()
    rounds_count = serializers.SerializerMethodField()
    total_pot_per_round = serializers.SerializerMethodField()
    total_collected = serializers.SerializerMethodField()
    total_paid_out = serializers.SerializerMethodField()
    current_round = serializers.SerializerMethodField()
    members = TontineMemberSerializer(many=True, read_only=True)
    rounds = TontineRoundSerializer(many=True, read_only=True)

    class Meta:
        model = TontineGroup
        fields = [
            'id', 'name', 'tontine_type', 'tontine_type_display',
            'contribution_amount', 'currency', 'frequency', 'frequency_display',
            'start_date', 'end_date', 'status', 'status_display',
            'account', 'account_name', 'late_penalty_amount',
            'description', 'rules', 'members_count', 'rounds_count',
            'total_pot_per_round', 'total_collected', 'total_paid_out',
            'current_round', 'members', 'rounds', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_members_count(self, obj):
        return obj.members.filter(status='ACTIVE').count()

    def get_rounds_count(self, obj):
        return obj.rounds.count()

    def get_total_pot_per_round(self, obj):
        active_members = obj.members.filter(status='ACTIVE')
        total_shares = sum([float(m.shares_count) for m in active_members])
        return float(obj.contribution_amount) * total_shares

    def get_total_collected(self, obj):
        tot = obj.contributions.filter(status='PAID').aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        return float(tot)

    def get_total_paid_out(self, obj):
        tot = obj.payouts.aggregate(tot=Sum('net_amount'))['tot'] or Decimal('0.00')
        return float(tot)

    def get_current_round(self, obj):
        current = obj.rounds.filter(status__in=['PENDING', 'COLLECTING', 'COLLECTED']).order_by('round_number').first()
        if current:
            return {
                'id': str(current.id),
                'round_number': current.round_number,
                'due_date': str(current.due_date),
                'beneficiary_name': current.beneficiary.full_name if current.beneficiary else None,
                'status': current.status,
                'collected_amount': float(current.collected_amount),
                'target_amount': float(current.target_amount)
            }
        return None

