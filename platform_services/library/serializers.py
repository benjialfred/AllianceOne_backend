from rest_framework import serializers
from .models import Book, BookLoan
from platform_services.education.students.serializers import StudentSerializer

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ('id',)

class BookLoanSerializer(serializers.ModelSerializer):
    book_details = BookSerializer(source='book', read_only=True)
    student_details = StudentSerializer(source='student', read_only=True)

    class Meta:
        model = BookLoan
        fields = '__all__'
        read_only_fields = ('id', 'loan_date', 'actual_return_date')
