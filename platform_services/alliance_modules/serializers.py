from rest_framework import serializers
from .models import Module, ModulePlan, ModuleInstallation

class ModulePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulePlan
        fields = ['id', 'name', 'price_monthly', 'price_yearly', 'currency', 'is_free', 'features']

class ModuleSerializer(serializers.ModelSerializer):
    plans = ModulePlanSerializer(many=True, read_only=True)
    
    class Meta:
        model = Module
        fields = [
            'id', 'slug', 'name', 'tagline', 'description', 'category', 
            'accent_color', 'icon_name', 'version', 'developer_name', 
            'is_verified', 'is_native', 'status', 'permissions', 'features', 'plans'
        ]

class ModuleInstallationSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(read_only=True)
    
    class Meta:
        model = ModuleInstallation
        fields = ['id', 'module', 'status', 'activated_at', 'settings']
