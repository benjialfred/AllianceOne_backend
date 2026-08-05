from django.urls import path, include
from rest_framework.routers import DefaultRouter
from platform_services.dashboards.api.views import DashboardLayoutViewSet

router = DefaultRouter()
router.register(r'layouts', DashboardLayoutViewSet, basename='dashboard-layout')

urlpatterns = [
    path('', include(router.urls)),
]
