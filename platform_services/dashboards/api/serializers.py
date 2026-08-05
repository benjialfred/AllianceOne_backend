from rest_framework import serializers
from platform_services.dashboards.models import DashboardLayout, WidgetPlacement

class WidgetPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetPlacement
        fields = ['id', 'widget_id', 'x', 'y', 'w', 'h', 'config']

class DashboardLayoutSerializer(serializers.ModelSerializer):
    widgets = WidgetPlacementSerializer(many=True, read_only=True)
    
    class Meta:
        model = DashboardLayout
        fields = ['id', 'name', 'is_default', 'widgets']
