import os
import glob
import re

base_path = r"d:\projets\projets pour entreprise\Alliance One\AlliancePlatform\platform_services\education"

def fix_views():
    for filepath in glob.glob(os.path.join(base_path, "**", "views.py"), recursive=True):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Inject TenantQuerySetMixin
        if "TenantQuerySetMixin" not in content:
            content = "from platform_services.identity.mixins import TenantQuerySetMixin\n" + content
            
        # Replace class XViewSet(viewsets.ModelViewSet):
        content = re.sub(r'class (\w+ViewSet)\(viewsets\.ModelViewSet\):', r'class \1(TenantQuerySetMixin, viewsets.ModelViewSet):', content)
        
        # Remove core.permissions imports
        content = re.sub(r'from core\.permissions import .*?\n', '', content)
        
        # Wipe get_permissions methods completely to avoid crashing on missing old classes
        content = re.sub(r'    def get_permissions\(self\):[\s\S]*?(?=    @|    def |class |$)', '', content)
        
        # Replace "from apps.classes.models" with "from platform_services.education.classes.models"
        content = re.sub(r'from apps\.(\w+)\.models', r'from platform_services.education.\1.models', content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

fix_views()
print("Views refactored")
