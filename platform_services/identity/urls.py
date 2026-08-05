from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import OrganizationViewSet, WorkspaceViewSet, UserViewSet, PersonViewSet, RoleViewSet, get_available_modules

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')
router.register(r'users', UserViewSet, basename='user')
router.register(r'persons', PersonViewSet, basename='person')
router.register(r'roles', RoleViewSet, basename='role')

urlpatterns = [
    path('modules/', get_available_modules, name='available_modules'),
    path('', include(router.urls)),
]
