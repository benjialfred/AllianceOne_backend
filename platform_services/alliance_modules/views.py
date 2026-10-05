from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Module, ModuleInstallation, ModulePlan
from .serializers import ModuleSerializer, ModuleInstallationSerializer
from .services import ModuleInstallationService
from platform_services.payments.providers.nelsius import NelsiusProvider
from platform_services.payments.models import AlliancePayment
import uuid
import logging

logger = logging.getLogger(__name__)

class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List all available modules in the Marketplace.
    """
    queryset = Module.objects.prefetch_related('plans').all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    pagination_class = None

class ModuleInstallationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List modules installed for the current user's organization.
    """
    serializer_class = ModuleInstallationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        # Assumes request.organization is set by a middleware (e.g. TenantMiddleware)
        # If not, we fall back to a generic filter (e.g. user's first org)
        if hasattr(self.request, 'organization') and self.request.organization:
            return ModuleInstallation.objects.filter(organization=self.request.organization)
        # Fallback: get installations for all organizations the user is a member of
        user_org_ids = self.request.user.memberships.values_list('organization_id', flat=True)
        return ModuleInstallation.objects.filter(organization_id__in=user_org_ids).distinct()

class InstallModuleView(views.APIView):
    """
    Endpoint to initiate the installation of a module.
    If the plan is free, installs immediately.
    If paid, returns a checkout URL.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, slug, *args, **kwargs):
        plan_id = request.data.get('plan_id')
        
        try:
            module = Module.objects.get(slug=slug)
        except Module.DoesNotExist:
            return Response({"error": "Module not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get organization from tenant middleware or user
        organization = getattr(request, 'tenant', None)
        if not organization:
            organization = getattr(request, 'organization', None)
        
        if not organization:
            # Fallback to memberships
            if hasattr(request.user, 'memberships') and request.user.memberships.exists():
                organization = request.user.memberships.first().organization
            elif hasattr(request.user, 'organizations') and request.user.organizations.exists():
                organization = request.user.organizations.first()
            else:
                from platform_services.identity.models import Organization
                organization, _ = Organization.objects.get_or_create(
                    name="Alliance One Default",
                    defaults={"legal_name": "Alliance One Default Inc."}
                )

        # Check if already installed
        if ModuleInstallation.objects.filter(organization=organization, module=module).exists():
            return Response({"error": "Module already installed"}, status=status.HTTP_400_BAD_REQUEST)

        # Get plan
        try:
            plan = ModulePlan.objects.get(id=plan_id, module=module) if plan_id else module.plans.filter(is_free=True).first()
        except ModulePlan.DoesNotExist:
            return Response({"error": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

        if not plan:
            return Response({"error": "No valid plan selected or available"}, status=status.HTTP_400_BAD_REQUEST)

        # Free Plan -> Install directly
        if plan.is_free:
            installation = ModuleInstallationService.install_module(
                organization=organization,
                module_slug=slug,
                user=request.user,
                plan_id=plan.id
            )
            return Response(ModuleInstallationSerializer(installation).data, status=status.HTTP_201_CREATED)

        # Paid Plan -> Initiate Checkout
        # Paid Plan -> Initiate Checkout
        # 1. Pre-create the installation in PENDING status
        installation = ModuleInstallationService.install_module(
            organization=organization,
            module_slug=slug,
            user=request.user,
            plan_id=plan.id,
            activate=False
        )

        # 2. Create AlliancePayment
        merchant_reference = f"MOD-{organization.id.hex[:8]}-{uuid.uuid4().hex[:8]}".upper()
        
        payment = AlliancePayment.objects.create(
            organization=organization,
            user=request.user,
            merchant_reference=merchant_reference,
            amount=plan.price_monthly, # Assuming monthly for simplicity here
            currency=plan.currency,
            metadata={
                "installation_id": str(installation.id),
                "module_slug": slug,
                "plan_id": str(plan.id)
            }
        )

        # 3. Call Nelsius
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        return_url = f"{frontend_url}/app/marketplace/callback?ref={merchant_reference}"
        cancel_url = f"{frontend_url}/app/marketplace"
        
        provider = NelsiusProvider()
        try:
            checkout_data = provider.initiate_checkout(payment, return_url, cancel_url)
            return Response({
                "checkout_url": checkout_data.get('checkout_url'),
                "merchant_reference": merchant_reference,
                "status": "PAYMENT_REQUIRED"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Checkout initiation failed: {str(e)}")
            return Response({"error": "Payment provider unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

