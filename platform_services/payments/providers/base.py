from abc import ABC, abstractmethod
from typing import Any, Dict
from decimal import Decimal
from ..models import AlliancePayment

class BasePaymentProvider(ABC):
    """
    Abstract Base Class for Payment Providers.
    All providers (Nelsius, Stripe, etc.) must implement this interface.
    """

    @abstractmethod
    def initiate_checkout(self, payment: AlliancePayment, return_url: str, cancel_url: str) -> Dict[str, Any]:
        """
        Initiate a checkout session.
        Should return a dictionary containing the redirect URL and any required tokens.
        """
        pass

    @abstractmethod
    def charge_directpay(self, payment: AlliancePayment, payment_method_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Charge a customer directly without redirecting (e.g. Server-to-Server API).
        """
        pass

    @abstractmethod
    def verify_transaction(self, provider_transaction_code: str) -> Dict[str, Any]:
        """
        Verify the status of a transaction with the provider.
        Must return a standardized dictionary containing at least:
        - 'status': 'COMPLETED', 'FAILED', 'PENDING'
        - 'amount': Decimal
        - 'currency': str
        - 'metadata': dict
        """
        pass
