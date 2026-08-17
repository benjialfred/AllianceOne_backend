from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookViewSet, BookLoanViewSet

router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book')
router.register(r'loans', BookLoanViewSet, basename='loan')

urlpatterns = [
    path('', include(router.urls)),
]
