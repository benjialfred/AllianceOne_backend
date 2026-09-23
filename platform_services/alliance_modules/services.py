import logging
from django.db import transaction
from django.utils import timezone
from .models import Module, ModuleInstallation, InstallationStatus, ModulePlan, Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)

class ModuleInstallationService:
    """
    Service responsible for installing, activating, and uninstalling modules for tenants.
    """

    @classmethod
    @transaction.atomic
    def install_module(cls, organization, module_slug: str, user=None, plan_id=None, activate: bool = True) -> ModuleInstallation:
        """
        Idempotent installation of a module.
        """
        try:
            module = Module.objects.get(slug=module_slug)
        except Module.DoesNotExist:
            raise ValueError(f"Module {module_slug} does not exist.")

        # select_for_update or get_or_create to prevent race conditions
        installation, created = ModuleInstallation.objects.select_for_update().get_or_create(
            organization=organization,
            module=module,
            defaults={
                'status': InstallationStatus.PENDING,
                'installed_by': user
            }
        )

        if not created and installation.status == InstallationStatus.ACTIVE:
            logger.info(f"Module {module_slug} is already active for {organization.name}.")
            return installation

        # If a plan is provided, handle subscription setup
        if plan_id:
            try:
                plan = ModulePlan.objects.get(id=plan_id, module=module)
                
                # Setup subscription (idempotent)
                Subscription.objects.get_or_create(
                    installation=installation,
                    defaults={
                        'organization': organization,
                        'plan': plan,
                        'status': SubscriptionStatus.ACTIVE if activate else SubscriptionStatus.PENDING
                    }
                )
            except ModulePlan.DoesNotExist:
                raise ValueError("Invalid Plan ID provided.")

        # For free modules or after payment verification, we activate immediately.
        if activate:
            cls.activate_installation(installation)

        return installation

    @classmethod
    def activate_installation(cls, installation: ModuleInstallation):
        """
        Activates the module.
        """
        if installation.status != InstallationStatus.ACTIVE:
            installation.status = InstallationStatus.ACTIVE
            installation.activated_at = timezone.now()
            installation.save(update_fields=['status', 'activated_at', 'updated_at'])
            
            # Activate Subscription if it exists
            if hasattr(installation, 'subscription') and installation.subscription:
                if installation.subscription.status != SubscriptionStatus.ACTIVE:
                    installation.subscription.status = SubscriptionStatus.ACTIVE
                    installation.subscription.save(update_fields=['status', 'updated_at'])

            # Post-activation hooks (e.g. creating default data for the module)
            cls._run_post_activation_hooks(installation)

    @classmethod
    def _run_post_activation_hooks(cls, installation: ModuleInstallation):
        """
        Runs hooks when a module is activated.
        """
        # Could dispatch a signal or call module-specific initialization routines
        pass
