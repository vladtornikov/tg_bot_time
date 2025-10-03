"""Encryption utilities for OAuth tokens."""
import base64
from typing import Union

from nacl.encoding import Base64Encoder
from nacl.secret import SecretBox
from nacl.utils import random

from config.settings import get_settings

settings = get_settings()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self, key: bytes = None):
        """Initialize encryption service with key."""
        if key is None:
            key = settings.encryption_key.encode()
        self.box = SecretBox(key)
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """Encrypt data and return base64 encoded string."""
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = self.box.encrypt(data, encoder=Base64Encoder)
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded encrypted data."""
        decrypted = self.box.decrypt(encrypted_data.encode(), encoder=Base64Encoder)
        return decrypted.decode()
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key."""
        key = random(SecretBox.KEY_SIZE)
        return base64.b64encode(key).decode()


# Global encryption service instance
encryption_service = EncryptionService()
