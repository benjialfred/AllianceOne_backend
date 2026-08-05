from django.conf import settings
from django.db import models

from platform_services.identity.models import TenantModel


class Activity(TenantModel):
    """
    Objet Universel : Activité (Timeline universelle).
    Tous les événements significatifs des modules y sont tracés.
    """
    action = models.CharField(max_length=255, help_text="Ex: INVOICE_CREATED, PAYMENT_RECEIVED")
    description = models.TextField(blank=True)
    module_source = models.CharField(max_length=100, help_text="Ex: billing, education, health")

    # L'acteur ayant déclenché l'activité (optionnel, peut être un système)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.action} via {self.module_source}"


class Conversation(TenantModel):
    """
    Objet Universel : Conversation (Chat, Support, Threads).
    """
    topic = models.CharField(max_length=255, blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.topic or f"Conversation {self.id}"


class Message(TenantModel):
    """
    Un message au sein d'une conversation.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender} in {self.conversation}"


class Notification(TenantModel):
    """
    Objet Universel : Notification (Email, SMS, Push).
    """
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=50, help_text="EMAIL, SMS, PUSH, IN_APP")
    title = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=50, default="PENDING", help_text="PENDING, SENT, FAILED")

    def __str__(self):
        return f"[{self.channel}] To {self.recipient}: {self.title}"
