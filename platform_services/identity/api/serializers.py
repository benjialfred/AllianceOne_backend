from rest_framework import serializers
from platform_services.identity.models import Organization, Workspace, User, Person, Role

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'legal_name', 'registration_number', 'created_at', 'updated_at']


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        # On n'expose pas organization, car elle est déduite du header par le mixin
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'created_at']


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ['id', 'first_name', 'last_name', 'date_of_birth', 'gender', 'full_name']
        read_only_fields = ['id', 'full_name']


class UserSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'is_active', 'person', 'created_at']
        read_only_fields = ['id', 'created_at']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']
