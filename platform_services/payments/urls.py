from django.urls import path
from .views import NelsiusWebhookVerifyView

urlpatterns = [
    path('verify/', NelsiusWebhookVerifyView.as_view(), name='payment-verify'),
]
