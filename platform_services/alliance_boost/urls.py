from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BoostServicesView, BoostOrderViewSet

router = DefaultRouter()
router.register(r'orders', BoostOrderViewSet, basename='boost-order')

urlpatterns = [
    path('services/', BoostServicesView.as_view(), name='boost-services'),
    path('', include(router.urls)),
]
