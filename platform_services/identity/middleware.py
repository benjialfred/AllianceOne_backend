from django.http import HttpRequest
from django.core.exceptions import ValidationError
from platform_services.identity.models import Organization

class TenantMiddleware:
    """
    Middleware qui simule l'appartenance à un Tenant (Organisation) pour faciliter les tests.
    Il lit l'en-tête 'X-Tenant-ID' et injecte l'organisation dans request.tenant.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Récupération de l'ID depuis l'en-tête (HTTP_X_TENANT_ID dans Django)
        tenant_id = request.META.get('HTTP_X_TENANT_ID')
        
        if tenant_id:
            if tenant_id == 'platform_admin':
                # Mock pour le frontend: On récupère ou on crée une organisation par défaut
                request.tenant, _ = Organization.objects.get_or_create(
                    name="Alliance One Default",
                    defaults={"legal_name": "Alliance One Default Inc."}
                )
                request.is_platform_admin = True
            else:
                try:
                    request.tenant = Organization.objects.get(id=tenant_id)
                except (Organization.DoesNotExist, ValidationError):
                    request.tenant = None
        else:
            request.tenant = None

        response = self.get_response(request)
        return response
