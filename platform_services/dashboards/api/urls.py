from django.urls import path, include
from rest_framework.routers import DefaultRouter
from platform_services.dashboards.api.views import DashboardLayoutViewSet
from platform_services.dashboards.api.hub_views import HubMetricsView

router = DefaultRouter()
router.register(r'layouts', DashboardLayoutViewSet, basename='dashboard-layout')

urlpatterns = [
    path('hub-metrics/', HubMetricsView.as_view(), name='hub-metrics'),
    path('', include(router.urls)),
]
