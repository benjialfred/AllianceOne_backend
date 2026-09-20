from django.urls import path, include
from rest_framework.routers import DefaultRouter
from platform_services.dashboards.api.views import DashboardLayoutViewSet
from platform_services.dashboards.api.hub_views import HubMetricsView
from platform_services.dashboards.api.hyperadmin_views import (
    HyperAdminOverviewView,
    HyperAdminOrganizationManageView,
    HyperAdminModuleToggleView,
    HyperAdminUserManageView
)

router = DefaultRouter()
router.register(r'layouts', DashboardLayoutViewSet, basename='dashboard-layout')

urlpatterns = [
    path('hub-metrics/', HubMetricsView.as_view(), name='hub-metrics'),
    path('hyperadmin/overview/', HyperAdminOverviewView.as_view(), name='hyperadmin-overview'),
    path('hyperadmin/organizations/', HyperAdminOrganizationManageView.as_view(), name='hyperadmin-org-create'),
    path('hyperadmin/organizations/<uuid:org_id>/toggle-module/', HyperAdminModuleToggleView.as_view(), name='hyperadmin-toggle-module'),
    path('hyperadmin/users/create/', HyperAdminUserManageView.as_view(), name='hyperadmin-user-create'),
    path('', include(router.urls)),
]
