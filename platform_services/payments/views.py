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

from rest_framework.permissions import IsAuthenticated
from .providers.nelsius import NelsiusProvider
from .models import AlliancePayment
import uuid

class InitiateCheckoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'XAF')
        description = request.data.get('description', 'Abonnement Alliance One Premium')
        return_url = request.data.get('return_url')
        cancel_url = request.data.get('cancel_url')

        if not amount or not return_url or not cancel_url:
            return Response({"error": "amount, return_url and cancel_url are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get organization from tenant middleware or user
        organization = getattr(request, 'tenant', None)
        if not organization:
            organization = getattr(request, 'organization', None)
        
        if not organization:
            if hasattr(request.user, 'organizations') and request.user.organizations.exists():
                organization = request.user.organizations.first()
            elif hasattr(request.user, 'memberships') and request.user.memberships.exists():
                organization = request.user.memberships.first().organization
            else:
                from platform_services.identity.models import Organization
                organization, _ = Organization.objects.get_or_create(
                    name="Alliance One Default",
                    defaults={"legal_name": "Alliance One Default Inc."}
                )

        # Create a pending payment record
        payment = AlliancePayment.objects.create(
            organization=organization,
            user=request.user,
            amount=amount,
            currency=currency,
            description=description,
            merchant_reference=f"AO_{uuid.uuid4().hex[:12].upper()}"
        )

        try:
            provider = NelsiusProvider()
            checkout_data = provider.initiate_checkout(payment, return_url, cancel_url)
            
            # Save provider reference
            payment.provider_transaction_code = checkout_data.get('transaction_code')
            payment.save()

            return Response({
                "checkout_url": checkout_data.get('checkout_url'),
                "reference": payment.merchant_reference,
                "transaction_code": payment.provider_transaction_code
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            payment.status = 'failed'
            payment.provider_message = str(e)
            payment.save()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
