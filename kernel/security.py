import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings

from .exceptions import SecurityError


class SecurityEngine:
    """
    Cryptographic utilities for the Kernel (encryption, hashing, secure randoms).
    This is totally agnostic and independent of Django's auth system.
    """

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """
        Derives a Fernet key from the Django SECRET_KEY.
        In production, a dedicated secret should be used.
        """
        secret = settings.SECRET_KEY.encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"alliance-os-kernel-salt",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret))
        return Fernet(key)

    @classmethod
    def encrypt_data(cls, data: str) -> str:
        """Encrypts a string into a base64-encoded encrypted string."""
        try:
            f = cls._get_fernet()
            return f.encrypt(data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            raise SecurityError(f"Encryption failed: {str(e)}") from e

    @classmethod
    def decrypt_data(cls, encrypted_data: str) -> str:
        """Decrypts a previously encrypted string."""
        try:
            f = cls._get_fernet()
            return f.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        except Exception as e:
            raise SecurityError(f"Decryption failed: {str(e)}") from e

    @classmethod
    def generate_secure_token(cls, length: int = 32) -> str:
        """Generates a secure, random hexadecimal token."""
        return os.urandom(length).hex()
