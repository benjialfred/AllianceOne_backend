from rest_framework import serializers
from .models import TuitionProfile, Payment
from platform_services.education.students.serializers import StudentSerializer

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'tuition_profile', 'amount', 'date', 'receipt_number', 'recorded_by')
        read_only_fields = ('id', 'date', 'receipt_number', 'recorded_by')

class TuitionProfileSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    student_details = StudentSerializer(source='student', read_only=True)
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = TuitionProfile
        fields = ('id', 'student', 'student_details', 'academic_year', 'total_amount', 'total_paid', 'remaining_amount', 'payments')
        read_only_fields = ('id',)

