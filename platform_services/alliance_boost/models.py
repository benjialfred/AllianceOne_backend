from django.db import models
from django.conf import settings
from platform_services.identity.models import TenantModel
from platform_services.payments.models import AlliancePayment

class BoostOrderStatus(models.TextChoices):
    PENDING = 'PENDING', 'En attente de paiement'
    PROCESSING = 'PROCESSING', 'En cours de traitement'
    COMPLETED = 'COMPLETED', 'Terminé'
    PARTIAL = 'PARTIAL', 'Partiellement terminé'
    CANCELED = 'CANCELED', 'Annulé'
    REFUNDED = 'REFUNDED', 'Remboursé'

class BoostOrder(TenantModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='boost_orders')
    
    # IzyBoost specific fields
    service_id = models.IntegerField(help_text="ID du service IzyBoost")
    service_name = models.CharField(max_length=255)
    target_link = models.URLField(max_length=1000, help_text="Lien du compte ou de la publication à booster")
    quantity = models.IntegerField()
    comments = models.TextField(blank=True, null=True, help_text="Commentaires personnalisés si nécessaire")
    
    # IzyBoost remote order tracking
    remote_order_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID de commande renvoyé par IzyBoost")
    start_count = models.CharField(max_length=50, blank=True, null=True)
    remains = models.CharField(max_length=50, blank=True, null=True)
    
    # Payment and Pricing
    cost_price_usd = models.DecimalField(max_digits=10, decimal_places=4, help_text="Coût réel facturé par IzyBoost en USD")
    selling_price = models.DecimalField(max_digits=14, decimal_places=2, help_text="Prix facturé au client final")
    currency = models.CharField(max_length=10, default='XAF')
    
    status = models.CharField(max_length=20, choices=BoostOrderStatus.choices, default=BoostOrderStatus.PENDING)
    payment = models.ForeignKey(AlliancePayment, on_delete=models.SET_NULL, null=True, blank=True, related_name='boost_orders')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Boost #{self.id} - {self.service_name} ({self.quantity}) - {self.status}"
