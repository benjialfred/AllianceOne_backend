from rest_framework import serializers

from .models import Grade, GradeHistory, SequenceValidation


class GradeSerializer(serializers.ModelSerializer):
    reason = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Grade
        fields = (
            'id',
            'student',
            'subject',
            'teacher',
            'sequence',
            'evaluation_type',
            'academic_year',
            'value',
            'comment',
            'reason',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class GradeHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeHistory
        fields = ('id', 'grade', 'old_value', 'new_value', 'reason', 'changed_at', 'changed_by')
        read_only_fields = ('id', 'changed_at')


class SequenceValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SequenceValidation
        fields = '__all__'
        read_only_fields = ('locked_at', 'locked_by')
