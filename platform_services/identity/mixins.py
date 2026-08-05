class TenantQuerySetMixin:
    """
    Mixin pour filtrer automatiquement les données selon le Tenant (Organisation) actif.
    Ce mixin s'applique aux vues DRF qui manipulent des TenantModel.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Si la requête possède un tenant, on filtre strictement.
        # Sinon, pour sécuriser par défaut, on retourne un QuerySet vide ou une erreur,
        # mais ici, comme c'est un mock permissif, on pourrait retourner vide.
        tenant = getattr(self.request, 'tenant', None)
        
        if tenant:
            return queryset.filter(organization=tenant)
            
        # Si aucun X-Tenant-ID n'est fourni, on bloque l'accès aux données tenantées.
        return queryset.none()

    def perform_create(self, serializer):
        """
        Assigne automatiquement l'organisation courante lors de la création d'un objet.
        """
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            serializer.save(organization=tenant)
        else:
            from rest_framework.exceptions import ValidationError
            # S'il n'y a pas de tenant, on ne peut pas créer un TenantModel
            raise ValidationError("Un X-Tenant-ID valide est requis pour créer cette ressource.")
