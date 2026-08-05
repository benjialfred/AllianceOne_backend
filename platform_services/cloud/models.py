from django.db import models

from platform_services.identity.models import TenantModel


class File(TenantModel):
    """
    Objet Universel : Fichier physique (Uploads, Médias).
    Gère le stockage abstrait (S3, local) et les métadonnées.
    """
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField(default=0)
    storage_path = models.TextField(help_text="Chemin S3 ou local")
    is_public = models.BooleanField(default=False)

    def __str__(self):
        return self.original_filename


class Document(TenantModel):
    """
    Objet Universel : Document logique (Facture, Contrat, Ordonnance).
    Peut lier plusieurs versions de Fichiers physiques.
    """
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=100, help_text="Ex: INVOICE, CONTRACT, PRESCRIPTION")
    status = models.CharField(max_length=50, default="DRAFT", help_text="DRAFT, SIGNED, ARCHIVED")

    # Fichier actuel actif (dernière version)
    current_file = models.OneToOneField(File, on_delete=models.SET_NULL, null=True, blank=True, related_name="active_in_document")

    def __str__(self):
        return f"[{self.document_type}] {self.title}"
