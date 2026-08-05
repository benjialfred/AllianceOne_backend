import os
import re

base_dir = r'd:\projets\projets pour entreprise\Alliance One\AlliancePlatform\platform_services\education'

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    if 'IsDirectorOrCensor' in content:
        new_content = new_content.replace('IsDirectorOrCensor', 'IsAuthenticated')
        # Add import if missing
        if 'from rest_framework.permissions import' not in new_content:
            new_content = new_content.replace('from rest_framework import viewsets', 'from rest_framework import viewsets\nfrom rest_framework.permissions import IsAuthenticated')
        elif 'IsAuthenticated' not in new_content:
            new_content = new_content.replace('from rest_framework.permissions import ', 'from rest_framework.permissions import IsAuthenticated, ')
            
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {filepath}')

for root, _, files in os.walk(base_dir):
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))
print('Done.')
