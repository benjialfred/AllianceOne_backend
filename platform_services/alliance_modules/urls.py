from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ModuleViewSet, ModuleInstallationViewSet, InstallModuleView

router = DefaultRouter()
router.register(r'registry', ModuleViewSet, basename='module-registry')
router.register(r'installations', ModuleInstallationViewSet, basename='module-installations')

urlpatterns = [
    path('', include(router.urls)),
    path('<slug:slug>/install/', InstallModuleView.as_view(), name='module-install'),
]
