from rest_framework import serializers
from platform_services.identity.models import Organization, Workspace, User, Person, Role, OrganizationProfile

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


class OrganizationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationProfile
        fields = [
            'id', 'sector', 'sub_sector', 'country', 'city',
            'employee_count', 'phone', 'website', 'logo_url',
            'selected_modules', 'onboarding_completed', 'onboarding_completed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OnboardingSubmitSerializer(serializers.Serializer):
    """Serializer pour la soumission du wizard d'onboarding."""
    # Organisation
    organization_name = serializers.CharField(max_length=255)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    # Profil
    sector = serializers.CharField(max_length=100)
    sub_sector = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=2, default='CM')
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    employee_count = serializers.CharField(max_length=50, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    # Modules
    selected_modules = serializers.ListField(child=serializers.CharField(), min_length=1)
