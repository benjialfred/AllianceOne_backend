import requests
from typing import Any, Dict
from django.conf import settings
from .base import BasePaymentProvider
from ..models import AlliancePayment, PaymentStatus

class NelsiusPaymentError(Exception):
    pass

class NelsiusProvider(BasePaymentProvider):
    """
    Nelsius Payment Provider Implementation.
    """
    
    def __init__(self):
        # Fetch from settings, fallback to some defaults for local dev if needed
        self.api_base_url = getattr(settings, 'NELSIUS_API_BASE_URL', 'http://localhost:8000/api/v1')
        self.secret_key = getattr(settings, 'NELSIUS_SECRET_KEY', 'sk_test_dev_key')
        
        self.headers = {
            'X-Api-Key': self.secret_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def initiate_checkout(self, payment: AlliancePayment, return_url: str, cancel_url: str) -> Dict[str, Any]:
        """
        Initiate a checkout session with Nelsius.
        """
        if not self.secret_key:
            raise NelsiusPaymentError("NELSIUS_SECRET_KEY is not configured.")

        url = f"{self.api_base_url}/checkout/initiate"
        
        payload = {
            "amount": float(payment.amount),
            "currency": payment.currency,
            "reference": payment.merchant_reference,
            "return_url": return_url,
            "cancel_url": cancel_url,
            "metadata": {
                "organization_id": str(payment.organization.id)
            }
        }
        if payment.user and payment.user.email:
            payload["customer_email"] = payment.user.email
        
        try:
            if self.secret_key == 'TEST_DEV_KEY':
                return {
                    "checkout_url": f"http://localhost:3000/checkout/CHK_{payment.merchant_reference}",
                    "transaction_code": f"CHK_{payment.merchant_reference}",
                    "reference": payment.merchant_reference,
                    "status": "pending"
                }

            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data.get('data', {})
            
        except requests.RequestException as e:
            raise NelsiusPaymentError(f"Nelsius checkout initiation failed: {str(e)}")

    def charge_directpay(self, payment: AlliancePayment, payment_method_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Direct pay (API to API) without redirect (Mobile Money Push USSD).
        """
        url = f"{self.api_base_url}/payments/charge"
        
        phone = payment_method_data.get('phone')
        operator = payment_method_data.get('operator')
        email = payment_method_data.get('email', getattr(payment.user, 'email', 'client@alliance.one'))
        
        if not phone or not operator:
            raise ValueError("Phone and operator are required for Direct Pay")

        payload = {
            "amount": float(payment.amount),
            "currency": payment.currency,
            "phone": phone,
            "operator": operator,
            "email": email,
            "reference": payment.merchant_reference
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data.get('data', {})
            
        except requests.RequestException as e:
            raise NelsiusPaymentError(f"Nelsius Direct Pay failed: {str(e)}")

    def verify_transaction(self, provider_transaction_code: str) -> Dict[str, Any]:
        """
        Verify the status of a transaction S2S using the merchant reference or transaction code.
        """
        if not self.secret_key:
            raise NelsiusPaymentError("NELSIUS_SECRET_KEY is not configured.")

        url = f"{self.api_base_url}/payments/{provider_transaction_code}"
        
        try:
            if self.secret_key == 'TEST_DEV_KEY':
                return {
                    "status": PaymentStatus.COMPLETED,
                    "amount": 5000,
                    "currency": "XAF",
                    "metadata": {}
                }

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            nelsius_status = data.get('data', {}).get('status', '').lower()
            
            internal_status = PaymentStatus.PENDING
            if nelsius_status == 'completed':
                internal_status = PaymentStatus.COMPLETED
            elif nelsius_status == 'failed':
                internal_status = PaymentStatus.FAILED
                
            return {
                "status": internal_status,
                "amount": data.get('data', {}).get('amount'),
                "currency": data.get('data', {}).get('currency'),
                "metadata": data.get('data', {}).get('metadata', {})
            }
            
        except requests.RequestException as e:
            raise NelsiusPaymentError(f"Nelsius verification failed: {str(e)}")
