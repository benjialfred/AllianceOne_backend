import os
import glob
import re

base_path = r"d:\projets\projets pour entreprise\Alliance One\AlliancePlatform\platform_services\education"

def fix_unique_together():
    for filepath in glob.glob(os.path.join(base_path, "**", "models.py"), recursive=True):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace unique_together = ('name', ...) with unique_together = ('organization', 'name', ...)
        # Find lines with unique_together
        def replace_unique(match):
            inner = match.group(1)
            # If organization is already there, skip
            if "'organization'" in inner or '"organization"' in inner:
                return match.group(0)
            return f"unique_together = ('organization', {inner})"
            
        content = re.sub(r"unique_together\s*=\s*\((.*?)\)", replace_unique, content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

fix_unique_together()
print("unique_together fixed")
