from django.db import models
from django.conf import settings
from platform_services.identity.models import UniversalObject, TenantModel

class ModuleCategory(models.TextChoices):
    CORE = 'CORE', 'Core Platform'
    OPERATIONS = 'OPERATIONS', 'Operations & Logistics'
    FINANCE = 'FINANCE', 'Finance & Accounting'
    PRODUCTIVITY = 'PRODUCTIVITY', 'Productivity & CRM'
    VERTICAL = 'VERTICAL', 'Vertical (Education, Health)'
    AI = 'AI', 'Artificial Intelligence'

class ModuleStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    BETA = 'BETA', 'Beta'
    MAINTENANCE = 'MAINTENANCE', 'Maintenance'
    DEPRECATED = 'DEPRECATED', 'Deprecated'

class Module(UniversalObject):
    """
    Central Registry for all Alliance One Modules (Marketplace).
    Not attached to a tenant (Global).
    """
    slug = models.SlugField(unique=True, help_text="Unique identifier (e.g. 'education', 'inventory')")
    name = models.CharField(max_length=100)
    tagline = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=ModuleCategory.choices, default=ModuleCategory.CORE)
    
    accent_color = models.CharField(max_length=20, default="#4f46e5")
    icon_name = models.CharField(max_length=50, default="Package")
    version = models.CharField(max_length=20, default="1.0.0")
    
    developer_name = models.CharField(max_length=100, default="Alliance Core Team")
    is_verified = models.BooleanField(default=True)
    is_native = models.BooleanField(default=True, help_text="Built-in Alliance module")
    
    status = models.CharField(max_length=20, choices=ModuleStatus.choices, default=ModuleStatus.ACTIVE)
    
    permissions = models.JSONField(default=list, help_text="List of permissions required by this module")
    features = models.JSONField(default=list, help_text="List of key features for display")

    class Meta:
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.slug})"

class ModulePlan(UniversalObject):
    """
    Pricing plans for a Module.
    """
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='plans')
    name = models.CharField(max_length=100, help_text="e.g. 'Starter', 'Professional'")
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default="XAF")
    is_free = models.BooleanField(default=False)
    features = models.JSONField(default=list)

    class Meta:
        verbose_name = "Module Plan"
        verbose_name_plural = "Module Plans"

    def __str__(self):
        return f"{self.module.name} - {self.name}"

class InstallationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Installation'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended (Billing Issue)'
    UNINSTALLED = 'UNINSTALLED', 'Uninstalled'

class ModuleInstallation(TenantModel):
    """
    Links a Module to an Organization (Tenant).
    Replaces the old active_modules JSON string.
    """
    module = models.ForeignKey(Module, on_delete=models.PROTECT, related_name='installations')
    status = models.CharField(max_length=20, choices=InstallationStatus.choices, default=InstallationStatus.PENDING)
    installed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True, help_text="Tenant-specific module configuration")

    class Meta:
        unique_together = ('organization', 'module')
        verbose_name = "Module Installation"
        verbose_name_plural = "Module Installations"

    def __str__(self):
        return f"{self.organization.name} -> {self.module.slug} ({self.status})"

class SubscriptionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Payment'
    TRIAL = 'TRIAL', 'Trial'
    ACTIVE = 'ACTIVE', 'Active'
    PAST_DUE = 'PAST_DUE', 'Past Due'
    CANCELED = 'CANCELED', 'Canceled'
    EXPIRED = 'EXPIRED', 'Expired'

class Subscription(TenantModel):
    """
    Represents an ongoing billing relationship for a ModulePlan.
    """
    installation = models.OneToOneField(ModuleInstallation, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(ModulePlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE)
    
    current_period_start = models.DateTimeField(auto_now_add=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"Sub: {self.installation.organization.name} - {self.plan.name}"
