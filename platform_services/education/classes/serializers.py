from rest_framework import serializers

from .models import AcademicYear, SchoolClass, AcademicEvent, Level, Section, SeriesGroup, Series

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

class SeriesGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeriesGroup
        fields = ('id', 'name')

class SeriesSerializer(serializers.ModelSerializer):
    group_details = SeriesGroupSerializer(source='group', read_only=True)
    class Meta:
        model = Series
        fields = ('id', 'name', 'group', 'group_details')

class SchoolClassSerializer(serializers.ModelSerializer):
    level_details = LevelSerializer(source='level', read_only=True)
    section_details = SectionSerializer(source='section', read_only=True)
    series_details = SeriesSerializer(source='series', read_only=True)
    
    class Meta:
        model = SchoolClass
        fields = ('id', 'name', 'level', 'level_details', 'section', 'section_details', 'series', 'series_details', 'academic_year', 'head_teacher', 'subjects', 'capacity', 'tuition_fee')
        read_only_fields = ('id',)

class AcademicEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicEvent
        fields = ('id', 'title', 'description', 'event_type', 'start_date', 'end_date', 'suspends_attendance', 'locks_grades', 'is_public', 'academic_year', 'created_at', 'created_by')
        read_only_fields = ('id', 'created_at', 'created_by')
