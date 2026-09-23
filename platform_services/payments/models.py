from django.db import models
from django.conf import settings
from platform_services.identity.models import TenantModel

class PaymentStatus(models.TextChoices):
    CREATED = 'CREATED', 'Created'
    PENDING = 'PENDING', 'Pending'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    EXPIRED = 'EXPIRED', 'Expired'
    REFUND_PENDING = 'REFUND_PENDING', 'Refund Pending'
    REFUNDED = 'REFUNDED', 'Refunded'

class PaymentType(models.TextChoices):
    CHECKOUT = 'CHECKOUT', 'Checkout (Hosted)'
    DIRECT_PAY = 'DIRECT_PAY', 'Direct Pay (API)'

class PaymentProvider(models.TextChoices):
    NELSIUS = 'NELSIUS', 'Nelsius'
    STRIPE = 'STRIPE', 'Stripe'
    PAYPAL = 'PAYPAL', 'PayPal'
    MANUAL = 'MANUAL', 'Manual/Bank Transfer'

class AlliancePayment(TenantModel):
    """
    Alliance One Central Payment Model.
    Acts as the source of truth for all incoming payments via various providers.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text="User who initiated the payment"
    )
    
    provider = models.CharField(max_length=50, choices=PaymentProvider.choices, default=PaymentProvider.NELSIUS)
    provider_transaction_code = models.CharField(max_length=255, blank=True, null=True, help_text="Transaction ID from the provider")
    merchant_reference = models.CharField(max_length=100, unique=True, help_text="Unique internal reference for idempotency (e.g. ALLIANCE-12345)")
    
    amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Exact amount paid")
    currency = models.CharField(max_length=10, default="XAF", help_text="Currency ISO code")
    
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.CREATED)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.CHECKOUT)
    
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional arbitrary data (e.g., checkout URLs, customer info)")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When the transaction was successfully verified S2S")

    class Meta:
        verbose_name = "Alliance Payment"
        verbose_name_plural = "Alliance Payments"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.merchant_reference} - {self.amount} {self.currency} ({self.status})"
