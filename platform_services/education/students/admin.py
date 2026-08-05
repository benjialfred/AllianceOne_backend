from django.contrib import admin

from .models import Student, Enrollment, Attendance

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('matricule', 'first_name', 'last_name', 'lifecycle_status', 'is_archived')
    search_fields = ('matricule', 'first_name', 'last_name')
    list_filter = ('lifecycle_status', 'is_archived')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'academic_year', 'school_class', 'decision', 'enrollment_date')
    search_fields = ('student__first_name', 'student__last_name', 'student__matricule')
    list_filter = ('academic_year', 'school_class', 'decision')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'is_absent', 'academic_year')
    search_fields = ('student__first_name', 'student__last_name')
    list_filter = ('is_absent', 'academic_year', 'date')
