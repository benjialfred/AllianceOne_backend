import uuid
from django.db import models
from django.conf import settings
from .orchestration import ExecutionPlanModel


class AIConversationModel(models.Model):
    """
    Persistent conversational session for Alliance AI.
    Scoped to an authenticated user and their tenant organization context.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_conversations'
    )
    organization_id = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=255, default="Nouvelle session")
    is_pinned = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alliance_ai_conversations"
        ordering = ['-is_pinned', '-updated_at']

    def __str__(self):
        return f"{self.title} ({self.id}) - Org: {self.organization_id}"


class AIMessageModel(models.Model):
    """
    Unit message belonging to an Alliance AI conversation.
    Supports rich structured content blocks and optional link to an operational execution plan (mission).
    """
    SENDER_USER = 'USER'
    SENDER_ASSISTANT = 'ASSISTANT'
    SENDER_SYSTEM = 'SYSTEM'
    SENDER_CHOICES = [
        (SENDER_USER, 'Utilisateur'),
        (SENDER_ASSISTANT, 'Alliance AI'),
        (SENDER_SYSTEM, 'Système'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        AIConversationModel,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES, default=SENDER_USER)
    content = models.TextField(blank=True, default='')
    structured_blocks = models.JSONField(null=True, blank=True)
    interaction_mode = models.CharField(max_length=50, default='DIRECT')
    mission = models.ForeignKey(
        ExecutionPlanModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages'
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alliance_ai_messages"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender}] {self.content[:40]}... ({self.conversation_id})"
