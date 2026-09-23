from django.contrib import admin
from .models import Module, ModulePlan, ModuleInstallation, Subscription

class ModulePlanInline(admin.TabularInline):
    model = ModulePlan
    extra = 1

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category', 'status', 'is_native', 'version')
    list_filter = ('category', 'status', 'is_native')
    search_fields = ('name', 'slug', 'tagline')
    inlines = [ModulePlanInline]

@admin.register(ModuleInstallation)
class ModuleInstallationAdmin(admin.ModelAdmin):
    list_display = ('organization', 'module', 'status', 'activated_at')
    list_filter = ('status', 'module__name')
    search_fields = ('organization__name', 'module__name')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('installation', 'plan', 'status', 'current_period_end')
    list_filter = ('status',)
    search_fields = ('installation__organization__name', 'plan__name')

