import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class UniversalObject(models.Model):
    """
    Classe de base pour tous les objets de la plateforme.
    Garantit l'utilisation d'UUIDv4 et des timestamps pour l'Offline-First.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    local_updated_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp du client (Offline-First)")
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


def default_modules():
    return ["education_core", "finance", "communication"]

class Organization(UniversalObject):
    """
    Objet Universel : Organisation.
    Sert de Tenant principal pour l'isolation des données (Multi-Tenant).
    """
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    active_modules = models.JSONField(default=default_modules, help_text="Liste des modules actifs pour cette organisation")

    def __str__(self):
        return self.name


def default_selected_modules():
    return []


class OrganizationProfile(models.Model):
    """
    Profil étendu de l'Organisation, collecté lors de l'onboarding.
    Stocke le secteur, la taille, la localisation et les modules choisis.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name='profile'
    )
    # Secteur d'activité
    sector = models.CharField(max_length=100, blank=True)
    sub_sector = models.CharField(max_length=100, blank=True)
    # Localisation
    country = models.CharField(max_length=2, default='CM', help_text="ISO 3166-1 alpha-2")
    city = models.CharField(max_length=100, blank=True)
    # Taille
    employee_count = models.CharField(max_length=50, blank=True, help_text="ex: 1-10, 11-50, 51-200")
    # Contact
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    # Modules sélectionnés à l'onboarding
    selected_modules = models.JSONField(default=default_selected_modules)
    # Onboarding status
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.organization.name}"


class TenantModel(UniversalObject):
    """
    Modèle de base pour toutes les entités métier (Modules).
    Garantit l'isolation stricte des données par Organisation.
    """
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="+")

    class Meta:
        abstract = True


class Workspace(TenantModel):
    """
    Espace de travail au sein d'une organisation (ex: "Département Santé", "Administration").
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class Person(UniversalObject):
    """
    Objet Universel : Personne.
    Toute entité humaine (Patient, Étudiant, Employé) hérite ou pointe vers Person.
    """
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=50, blank=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Address(UniversalObject):
    """
    Objet Universel : Adresse.
    """
    street_line_1 = models.CharField(max_length=255)
    street_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2") # Ex: CM, FR

    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.CASCADE, related_name="addresses")
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.CASCADE, related_name="addresses")


class UserManager(BaseUserManager):
    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est requise.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, UniversalObject):
    """
    Alliance ID : Modèle Utilisateur global.
    Un utilisateur peut appartenir à plusieurs Organisations.
    """
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Lien vers l'Objet Universel Person
    person = models.OneToOneField(Person, on_delete=models.PROTECT, null=True, blank=True, related_name="user_account")

    objects = UserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email


class Team(TenantModel):
    """
    Équipe au sein d'un Workspace ou d'une Organisation.
    """
    name = models.CharField(max_length=100)
    workspace = models.ForeignKey(Workspace, null=True, blank=True, on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name="teams")


class Role(TenantModel):
    """
    Rôle (RBAC) au sein d'une organisation.
    """
    name = models.CharField(max_length=100) # Ex: "Doctor", "Teacher", "Director"
    description = models.TextField(blank=True)


class Membership(TenantModel):
    """
    Table de liaison définissant l'accès d'un Utilisateur à une Organisation.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.ForeignKey(Role, on_delete=models.PROTECT)

    class Meta:
        unique_together = ('user', 'organization')
