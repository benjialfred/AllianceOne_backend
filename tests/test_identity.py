import pytest

from platform_services.identity.models import Organization, Person, User


@pytest.mark.django_db
def test_organization_and_user_creation():
    # 1. Création du Tenant (Organisation)
    org = Organization.objects.create(
        name="Clinique Saint-Luc",
        legal_name="SAS Clinique Saint-Luc"
    )
    assert org.id is not None
    assert org.name == "Clinique Saint-Luc"

    # 2. Création de l'Objet Universel Personne
    person = Person.objects.create(
        first_name="benjamin",
        last_name="Fraide"
    )
    assert person.full_name == "benjamin Fraide"

    # 3. Création du Compte Utilisateur Global lié à la Personne
    user = User.objects.create(
        email="benjamin.fraide@clinique.com",
        person=person
    )
    assert user.email == "benjamin.fraide@clinique.com"
    assert user.person.first_name == "benjamin"
    assert user.id is not None
