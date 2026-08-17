import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
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
