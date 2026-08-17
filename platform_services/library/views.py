from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import Book, BookLoan
from .serializers import BookSerializer, BookLoanSerializer
from platform_services.identity.mixins import TenantQuerySetMixin

class BookViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

class BookLoanViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = BookLoan.objects.all()
    serializer_class = BookLoanSerializer
    filterset_fields = ['student', 'book', 'status']

    def perform_create(self, serializer):
        # Reduce available quantity of the book
        book = serializer.validated_data['book']
        if book.available_quantity > 0:
            book.available_quantity -= 1
            book.save()
            serializer.save()
        else:
            raise Exception("Livre non disponible.")

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        loan = self.get_object()
        if loan.status in ['RETURNED']:
            return Response({"error": "Livre déjà retourné."}, status=status.HTTP_400_BAD_REQUEST)
        
        loan.status = 'RETURNED'
        loan.actual_return_date = timezone.now().date()
        loan.save()

        # Increase available quantity
        book = loan.book
        book.available_quantity += 1
        book.save()

        return Response({"success": "Livre retourné avec succès."})
