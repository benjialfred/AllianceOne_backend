from django.contrib import admin

from .models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('code', 'first_name', 'last_name', 'specialty')
    search_fields = ('code', 'first_name', 'last_name')
