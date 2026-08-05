# Alliance Cloud (Platform Service)

## Rôle
**Alliance Cloud** est le produit chargé du stockage de fichiers, de la gestion des médias, de l'archivage légal et des sauvegardes pour l'ensemble de l'OS Alliance One.

## Responsabilités
- **Abstraction du Stockage :** Gère l'écriture et la lecture vers AWS S3, MinIO, ou le système de fichiers local.
- **CDN & Cache :** Optimisation et distribution des médias (images, vidéos).
- **Documents & Versioning :** Gestion des versions d'un fichier (ex: Contrat v1, v2).
- **Sauvegardes et Restauration :** Points de sauvegarde et exports.
- **Sécurité et Chiffrement :** Chiffrement des fichiers au repos.

## Dépendances
- **Autorisées :** `Kernel`.
- **Interdites :** `Business Modules`. Alliance Cloud est un service transverse.

## API & Utilisation
Les modules n'utilisent jamais l'API de stockage Django par défaut, mais passent par Alliance Cloud :
```python
from platform.cloud.storage import upload_document

file_url = upload_document(file_object, bucket="invoices", secure=True)
```

## Événements Émis
- `DocumentUploaded`, `FileDeleted`, `BackupCompleted`
