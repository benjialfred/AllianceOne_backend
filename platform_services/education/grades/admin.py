from django.contrib import admin

from .models import Grade, GradeHistory


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'sequence', 'academic_year', 'value')
    list_filter = ('sequence', 'academic_year', 'subject')
    search_fields = ('student__matricule', 'student__first_name', 'student__last_name')


@admin.register(GradeHistory)
class GradeHistoryAdmin(admin.ModelAdmin):
    list_display = ('grade', 'old_value', 'new_value', 'changed_at', 'changed_by')
