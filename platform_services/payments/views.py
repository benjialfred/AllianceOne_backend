from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .verification import PaymentVerificationService
import logging

logger = logging.getLogger(__name__)

class NelsiusWebhookVerifyView(views.APIView):
    """
    Endpoint for Server-to-Server callbacks from Nelsius.
    Could also be called by the frontend after redirect to double check.
    """
    permission_classes = [AllowAny] # S2S endpoint, could add HMAC signature validation later

    def post(self, request, *args, **kwargs):
        merchant_reference = request.data.get('merchant_reference')
        provider_transaction_code = request.data.get('transaction_id')

        if not merchant_reference:
            return Response({"error": "merchant_reference is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = PaymentVerificationService.verify_payment(merchant_reference, provider_transaction_code)
            
            return Response({
                "status": payment.status,
                "merchant_reference": payment.merchant_reference,
                "amount": str(payment.amount),
                "currency": payment.currency
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Webhook verify error: {str(e)}")
            return Response({"error": "Internal server error during verification"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
