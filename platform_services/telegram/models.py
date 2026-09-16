import uuid
from django.db import models

class TelegramUpdateLog(models.Model):
    """
    Ensures idempotence for incoming Telegram updates.
    Telegram may re-deliver the exact same update_id during network retries.
    Logging every update_id guarantees single-execution semantics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    update_id = models.BigIntegerField(unique=True, db_index=True)
    telegram_user_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    command = models.CharField(max_length=100, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram Update Log"
        verbose_name_plural = "Telegram Update Logs"
        ordering = ['-processed_at']

    def __str__(self):
        return f"Update {self.update_id} ({self.command or 'generic'}) at {self.processed_at}"
