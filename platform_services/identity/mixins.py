from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

class TenantQuerySetMixin:
    """
    Mixin pour filtrer automatiquement les données selon le Tenant (Organisation) actif.
    Ce mixin sécurise l'accès multi-tenant en vérifiant l'appartenance (Membership).
    """
    
    def get_tenant(self):
        """
        Résout le tenant à partir du Header X-Tenant-ID et vérifie l'autorisation.
        Cache le résultat sur self.request.tenant.
        """
        if hasattr(self.request, 'tenant'):
            return self.request.tenant
            
        tenant_id = self.request.META.get('HTTP_X_TENANT_ID')
        self.request.tenant = None
        
        if not tenant_id:
            # Cas par défaut pour le développement ou l'admin
            if self.request.user.is_superuser:
                from platform_services.identity.models import Organization
                # Fallback to default organization if any
                org = Organization.objects.first()
                if org:
                    self.request.tenant = org
            return self.request.tenant
            
        try:
            from platform_services.identity.models import Organization, Membership
            org = Organization.objects.get(id=tenant_id)
            
            # Vérifie l'appartenance
            if self.request.user.is_superuser:
                self.request.tenant = org
            elif Membership.objects.filter(user=self.request.user, organization=org).exists():
                self.request.tenant = org
            else:
                raise PermissionDenied("Vous n'appartenez pas à cette organisation.")
                
        except (Organization.DoesNotExist, ValidationError):
            raise PermissionDenied("Organisation invalide ou introuvable.")
            
        return self.request.tenant

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant = self.get_tenant()
        
        if tenant:
            return queryset.filter(organization=tenant)
            
        # Si aucun tenant n'est résolu, on bloque l'accès
        return queryset.none()

    def perform_create(self, serializer):
        """
        Assigne automatiquement l'organisation courante lors de la création d'un objet.
        """
        tenant = self.get_tenant()
        if tenant:
            serializer.save(organization=tenant)
        else:
            from rest_framework.exceptions import ValidationError as DRFValidationError
            raise DRFValidationError("Un X-Tenant-ID valide est requis pour créer cette ressource.")
