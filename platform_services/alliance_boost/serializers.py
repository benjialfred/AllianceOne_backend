from rest_framework import serializers
from .models import BoostOrder, BoostOrderStatus

class BoostOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoostOrder
        fields = [
            'id', 'service_id', 'service_name', 'target_link', 
            'quantity', 'comments', 'selling_price', 'currency', 
            'status', 'start_count', 'remains', 'created_at'
        ]
        read_only_fields = ['id', 'selling_price', 'currency', 'status', 'start_count', 'remains', 'created_at']

class CreateBoostOrderSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    target_link = serializers.URLField()
    quantity = serializers.IntegerField(min_value=1)
    comments = serializers.CharField(required=False, allow_blank=True)
    
class BoostServiceSerializer(serializers.Serializer):
    service = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField()
    category = serializers.CharField()
    rate = serializers.CharField()
    min = serializers.IntegerField()
    max = serializers.IntegerField()
    refill = serializers.BooleanField(required=False)
    cancel = serializers.BooleanField(required=False)
