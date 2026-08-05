import os
import glob
import re

base_path = r"d:\projets\projets pour entreprise\Alliance One\AlliancePlatform\platform_services\education"

def process_models():
    for filepath in glob.glob(os.path.join(base_path, "**", "models.py"), recursive=True):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add import for TenantModel if not present
        if 'TenantModel' not in content:
            import_statement = "from platform_services.identity.models import TenantModel\n"
            content = import_statement + content
        
        # Replace models.Model with TenantModel, but not for AbstractBaseUser, etc.
        # Be careful not to replace inner models.Model
        content = re.sub(r'class (\w+)\(models\.Model\):', r'class \1(TenantModel):', content)
        
        # Replace 'accounts.User' with settings.AUTH_USER_MODEL or 'identity.User'
        content = content.replace("'accounts.User'", "settings.AUTH_USER_MODEL")
        if "settings.AUTH_USER_MODEL" in content and "from django.conf import settings" not in content:
            content = "from django.conf import settings\n" + content

        # Replace 'accounts' with 'identity' in general if any other relations exist, but maybe not necessary right now.

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

def process_apps():
    for filepath in glob.glob(os.path.join(base_path, "**", "apps.py"), recursive=True):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Update name = 'apps.students' to name = 'platform_services.education.students'
        content = re.sub(r"name = 'apps\.(\w+)'", r"name = 'platform_services.education.\1'", content)
        content = re.sub(r'name = "apps\.(\w+)"', r'name = "platform_services.education.\1"', content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

process_models()
process_apps()
print("Refactoring complete.")
