from django.db import models
from platform_services.identity.models import TenantModel
from platform_services.education.students.models import Student

class Book(TenantModel):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    year_published = models.IntegerField(null=True, blank=True)
    total_quantity = models.PositiveIntegerField(default=1)
    available_quantity = models.PositiveIntegerField(default=1)
    cover_image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title

class BookLoan(TenantModel):
    STATUS_CHOICES = (
        ('BORROWED', 'En cours'),
        ('RETURNED', 'Retourné'),
        ('LATE', 'En retard'),
        ('LOST', 'Perdu'),
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='loans')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='book_loans')
    loan_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BORROWED')

    def __str__(self):
        return f"{self.book.title} - {self.student.first_name}"
