import logging
from django.db import transaction
from django.utils import timezone
from .models import AlliancePayment, PaymentStatus, PaymentProvider
from .providers.nelsius import NelsiusProvider

logger = logging.getLogger(__name__)

class PaymentVerificationService:
    """
    Service responsible for verifying payments robustly, ensuring idempotency,
    and triggering downstream actions (like module installations).
    """

    @classmethod
    def get_provider_instance(cls, provider_name: str):
        if provider_name == PaymentProvider.NELSIUS:
            return NelsiusProvider()
        raise NotImplementedError(f"Provider {provider_name} not implemented.")

    @classmethod
    @transaction.atomic
    def verify_payment(cls, merchant_reference: str, provider_transaction_code: str) -> AlliancePayment:
        """
        Verifies a payment securely with Server-to-Server checks.
        Locks the row to prevent race conditions (double processing).
        """
        try:
            # select_for_update locks this row until the transaction commits or rolls back
            payment = AlliancePayment.objects.select_for_update().get(merchant_reference=merchant_reference)
        except AlliancePayment.DoesNotExist:
            logger.error(f"Verification failed: Payment {merchant_reference} not found.")
            raise ValueError(f"Payment with reference {merchant_reference} not found.")

        # If already completed or failed, return idempotently (don't re-process)
        if payment.status in [PaymentStatus.COMPLETED, PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
            logger.info(f"Payment {merchant_reference} already processed (Status: {payment.status}).")
            return payment

        # Update transaction code if we just received it
        if not payment.provider_transaction_code and provider_transaction_code:
            payment.provider_transaction_code = provider_transaction_code
            payment.save(update_fields=['provider_transaction_code'])

        provider = cls.get_provider_instance(payment.provider)

        # Contact provider to verify status
        try:
            verification_data = provider.verify_transaction(payment.provider_transaction_code or merchant_reference)
            
            new_status = verification_data.get('status')
            
            # If status changed to COMPLETED, record the time and trigger actions
            if new_status == PaymentStatus.COMPLETED:
                payment.status = PaymentStatus.COMPLETED
                payment.verified_at = timezone.now()
                payment.save(update_fields=['status', 'verified_at', 'updated_at'])
                
                # Trigger Module Installation / Subscription Activation hook here
                cls._on_payment_success(payment)
                
            elif new_status in [PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
                payment.status = new_status
                payment.save(update_fields=['status', 'updated_at'])

            return payment
            
        except Exception as e:
            logger.error(f"Error during payment verification for {merchant_reference}: {str(e)}")
            # In case of API failure, we might leave it PENDING to retry later
            raise e

    @classmethod
    def _on_payment_success(cls, payment: AlliancePayment):
        """
        Hook called when a payment is definitively marked as COMPLETED.
        """
        try:
            # Avoid circular import at module level
            from platform_services.alliance_modules.services import ModuleInstallationService
            from platform_services.alliance_modules.models import ModuleInstallation
            
            # Check metadata for installation instructions
            metadata = payment.metadata or {}
            installation_id = metadata.get('installation_id')
            
            if installation_id:
                installation = ModuleInstallation.objects.get(id=installation_id)
                ModuleInstallationService.activate_installation(installation)
                logger.info(f"Successfully activated module installation {installation_id} after payment {payment.merchant_reference}.")
        except Exception as e:
            logger.error(f"Error in _on_payment_success hook for payment {payment.id}: {str(e)}")
