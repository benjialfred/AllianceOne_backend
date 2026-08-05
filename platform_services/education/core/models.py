from django.db import models

class EducationErrorLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    status_code = models.IntegerField()
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    user_identifier = models.CharField(max_length=255, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    stack_trace = models.TextField(blank=True, null=True)
    payload = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        db_table = 'education_error_logs'

    def __str__(self):
        return f"{self.status_code} - {self.method} {self.path} ({self.timestamp})"


class AuditTrail(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('identity.User', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        db_table = 'education_audit_trail'
        verbose_name = 'Audit Trail'
        verbose_name_plural = 'Audit Trails'

    def __str__(self):
        return f"{self.user} - {self.action} on {self.entity_type} ({self.timestamp})"
