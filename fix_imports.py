import os
import re

base_dir = r'd:\projets\projets pour entreprise\Alliance One\AlliancePlatform\platform_services\education'

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Special case for SchoolSettings
    new_content = re.sub(
        r'from apps\.core\.models import SchoolSettings\n\s*settings = SchoolSettings\.get_settings\(\)',
        r'settings = student.organization',
        content
    )
    new_content = new_content.replace('settings.school_name', 'settings.name')
    new_content = new_content.replace('settings.motto or \'\'', "''")

    # General replacements
    new_content = new_content.replace('from apps.', 'from platform_services.education.')
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {filepath}')

for root, _, files in os.walk(base_dir):
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))
print('Done.')
