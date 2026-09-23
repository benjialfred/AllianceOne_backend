from django.contrib import admin
from .models import AlliancePayment

@admin.register(AlliancePayment)
class AlliancePaymentAdmin(admin.ModelAdmin):
    list_display = ('merchant_reference', 'organization', 'amount', 'currency', 'status', 'provider', 'created_at')
    list_filter = ('status', 'provider', 'payment_type')
    search_fields = ('merchant_reference', 'provider_transaction_code', 'organization__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'verified_at')

