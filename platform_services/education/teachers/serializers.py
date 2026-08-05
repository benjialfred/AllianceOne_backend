from rest_framework import serializers

from .models import Teacher


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ('id', 'user', 'code', 'first_name', 'last_name', 'sex', 'phone', 'email', 'specialty')
        read_only_fields = ('id', 'code')
