from django.contrib import admin

from .models import AcademicYear, SchoolClass, Level, Section, AcademicEvent

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('label', 'start_year', 'end_year', 'is_active', 'is_archived')
    list_filter = ('is_active', 'is_archived')

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'section', 'academic_year', 'head_teacher', 'capacity')
    list_filter = ('academic_year', 'level', 'section')

@admin.register(AcademicEvent)
class AcademicEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'start_date', 'end_date', 'academic_year', 'is_public')
    list_filter = ('academic_year', 'event_type', 'is_public')
