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

class ModuleInstallationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List modules installed for the current user's organization.
    """
    serializer_class = ModuleInstallationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Assumes request.organization is set by a middleware (e.g. TenantMiddleware)
        # If not, we fall back to a generic filter (e.g. user's first org)
        if hasattr(self.request, 'organization') and self.request.organization:
            return ModuleInstallation.objects.filter(organization=self.request.organization)
        # Fallback: get installations for all organizations the user is a member of
        return ModuleInstallation.objects.filter(organization__memberships__user=self.request.user).distinct()

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

        organization = getattr(request, 'organization', None)
        if not organization:
            # Fallback
            membership = request.user.memberships.first()
            if not membership:
                return Response({"error": "User has no organization"}, status=status.HTTP_403_FORBIDDEN)
            organization = membership.organization

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
        return_url = f"http://localhost:5173/app/marketplace/callback?ref={merchant_reference}"
        cancel_url = f"http://localhost:5173/app/marketplace"
        
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

