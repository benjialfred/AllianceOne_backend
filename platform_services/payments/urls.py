from django.urls import path
from .views import NelsiusWebhookVerifyView, InitiateCheckoutView

urlpatterns = [
    path('verify/', NelsiusWebhookVerifyView.as_view(), name='payment-verify'),
    path('checkout/initiate/', InitiateCheckoutView.as_view(), name='checkout-initiate'),
]
