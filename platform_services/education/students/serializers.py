from rest_framework import serializers

from .models import Student, Attendance, Enrollment
from platform_services.education.classes.serializers import SchoolClassSerializer, AcademicYearSerializer

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ('id',)

class EnrollmentSerializer(serializers.ModelSerializer):
    school_class_details = SchoolClassSerializer(source='school_class', read_only=True)
    academic_year_details = AcademicYearSerializer(source='academic_year', read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = ('id', 'enrollment_date')

class StudentSerializer(serializers.ModelSerializer):
    current_enrollment = serializers.SerializerMethodField()
    enrollments = EnrollmentSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = (
            'id',
            'matricule',
            'first_name',
            'last_name',
            'sex',
            'date_of_birth',
            'place_of_birth',
            'photo',
            'lifecycle_status',
            'parent_name',
            'parent_phone',
            'parent_address',
            'is_archived',
            'current_enrollment',
            'enrollments'
        )
        read_only_fields = ('id', 'matricule')

    def get_current_enrollment(self, obj):
        # Assumes the latest academic year is the current one
        enrollment = obj.enrollments.first()
        if enrollment:
            return EnrollmentSerializer(enrollment).data
        return None
