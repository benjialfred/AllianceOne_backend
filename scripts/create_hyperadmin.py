import os
import sys
import django

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alliance_platform.settings')
django.setup()

from django.contrib.auth import authenticate
from platform_services.identity.models import User, Person, Organization, OrganizationProfile, Role, Membership

def create_hyperadmin():
    email = "hyperadmin@alliance-one.com"
    password = "HyperAdmin@Alliance2026!"

    print(f"[*] Provisioning Hyperadmin user: {email}")

    # 1. Organization
    org = Organization.objects.first()
    if not org:
        org = Organization.objects.create(
            name="Alliance One HQ",
            legal_name="Alliance One Technologies Inc.",
            registration_number="RC-AO-2026-001",
            active_modules=["education_core", "finance", "inventory", "library", "tasks", "founder"]
        )
        print(f"[+] Created HQ Organization: {org.name}")

    profile, _ = OrganizationProfile.objects.get_or_create(
        organization=org,
        defaults={
            'sector': 'Technologies & Écosystème',
            'country': 'CM',
            'city': 'Douala',
            'employee_count': '51-200',
            'selected_modules': org.active_modules,
            'onboarding_completed': True
        }
    )
    if not profile.onboarding_completed:
        profile.onboarding_completed = True
        profile.save()

    # 2. Person
    person, _ = Person.objects.get_or_create(
        first_name="Hyper",
        last_name="Admin",
        defaults={"gender": "M"}
    )

    # 3. User
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
            "person": person
        }
    )

    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.person = person
    user.set_password(password)
    user.save()

    print(f"[+] User account {'created' if created else 'updated'}: {user.email}")

    # 4. Role & Membership
    role, _ = Role.objects.get_or_create(
        organization=org,
        name="HYPERADMIN",
        defaults={"description": "Super Administrateur Global de la plateforme Alliance One"}
    )

    membership, m_created = Membership.objects.get_or_create(
        user=user,
        organization=org,
        defaults={"role": role}
    )
    if not m_created and membership.role != role:
        membership.role = role
        membership.save()

    print(f"[+] Membership linked to {org.name} with role {role.name}")

    # 5. Verify Authentication
    auth_user = authenticate(email=email, password=password)
    if auth_user:
        print("[SUCCESS] User authentication verified successfully!")
        print("-" * 50)
        print(f"Email       : {email}")
        print(f"Password    : {password}")
        print(f"Role        : {role.name}")
        print(f"Superuser   : {user.is_superuser}")
        print(f"Staff       : {user.is_staff}")
        print("-" * 50)
    else:
        print("[ERROR] Authentication verification failed!")

if __name__ == '__main__':
    create_hyperadmin()
