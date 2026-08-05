from rest_framework import serializers

from .models import AcademicYear, SchoolClass, AcademicEvent, Level, Section

class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ('id', 'label', 'start_year', 'end_year', 'is_active', 'is_archived', 'created_at')
        read_only_fields = ('id', 'created_at')

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ('id', 'name', 'order')

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ('id', 'name')

class SchoolClassSerializer(serializers.ModelSerializer):
    level_details = LevelSerializer(source='level', read_only=True)
    section_details = SectionSerializer(source='section', read_only=True)
    
    class Meta:
        model = SchoolClass
        fields = ('id', 'name', 'level', 'level_details', 'section', 'section_details', 'academic_year', 'head_teacher', 'subjects', 'capacity')
        read_only_fields = ('id',)

class AcademicEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicEvent
        fields = ('id', 'title', 'description', 'event_type', 'start_date', 'end_date', 'suspends_attendance', 'locks_grades', 'is_public', 'academic_year', 'created_at', 'created_by')
        read_only_fields = ('id', 'created_at', 'created_by')
