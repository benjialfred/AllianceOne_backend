"""
URL configuration for alliance_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from platform_services.identity.auth_views import SimpleLoginView, GoogleAuthView, RegisterView

def api_root(request):
    return JsonResponse({
        "status": "online",
        "message": "Bienvenue sur l'API de Alliance Platform",
        "frontend_url": "http://localhost:5173"
    })

urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/core/auth/login/', SimpleLoginView.as_view(), name='auth-login'),
    path('api/core/auth/google/', GoogleAuthView.as_view(), name='auth-google'),
    path('api/core/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/core/identity/', include('platform_services.identity.urls')),
    path('api/core/dashboards/', include('platform_services.dashboards.api.urls')),
    path('api/core/ai/', include('platform_services.alliance_ai.urls')),
    path('api/core/payments/', include('platform_services.payments.urls')),
    path('api/core/modules/', include('platform_services.alliance_modules.urls')),
    path('api/education/', include('platform_services.education.api.urls')),
    path('api/inventory/', include('platform_services.inventory.urls')),
    path('api/library/', include('platform_services.library.urls')),
    path('api/finance/', include('platform_services.finance.urls')),
    path('api/tasks/', include('platform_services.tasks.urls')),
    path('api/founder/', include('platform_services.founder.urls')),
    path('api/integrations/telegram/', include('platform_services.telegram.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
