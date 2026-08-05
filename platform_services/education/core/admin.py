from django.contrib import admin
from .models import EducationErrorLog, AuditTrail

@admin.register(EducationErrorLog)
class EducationErrorLogAdmin(admin.ModelAdmin):
    list_display = ('status_code', 'method', 'path', 'timestamp', 'user_identifier')
    list_filter = ('status_code', 'method', 'timestamp')
    search_fields = ('path', 'user_identifier', 'error_message')

@admin.register(AuditTrail)
class AuditTrailAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'entity_type', 'entity_id')
    list_filter = ('action', 'entity_type', 'timestamp')
    search_fields = ('user__email', 'entity_id', 'reason')
