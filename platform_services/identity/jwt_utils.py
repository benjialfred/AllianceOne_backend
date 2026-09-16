import base64
import json

def decode_google_jwt(token: str):
    """
    Décode la charge utile (payload) d'un token JWT Google sans vérification cryptographique distante.
    Permet l'extraction sécurisée de l'email et des métadonnées de profil.
    """
    try:
        parts = token.split('.')
        if len(parts) < 2:
            return None
        payload = parts[1]
        padded = payload + '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded.decode('utf-8'))
    except Exception:
        return None
