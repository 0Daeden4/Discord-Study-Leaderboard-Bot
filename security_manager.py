import hashlib
import bcrypt
from cryptography.fernet import Fernet
import os

# AI generated but manually controlled for correctness and reliability


class SecurityManager:
    """Handles hashing and encryption operations."""

    @staticmethod
    def generate_lobby_hash(lobby_name: str) -> str:
        """
        Creates a hash for a lobby ID.
        """
        hasher = hashlib.sha256()
        hasher.update(lobby_name.encode('utf-8'))
        return hasher.hexdigest()

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hashes a password using bcrypt.
        """
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')

    @staticmethod
    def check_password(password: str, hashed_password: str) -> bool:
        """
        Checks if a plain-text password matches a bcrypt hash.
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    @staticmethod
    def generate_encryption_key() -> bytes:
        """Generates a new Fernet key for encryption."""
        return Fernet.generate_key()

    @staticmethod
    def encrypt_data(data: str, key: bytes) -> str:
        """Encrypts a string using the provided key."""
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode('utf-8'))
        return encrypted_data.decode('utf-8')

    @staticmethod
    def decrypt_data(encrypted_data: str, key: bytes) -> str:
        """Decrypts a string using the provided key."""
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data.encode('utf-8'))
        return decrypted_data.decode('utf-8')
