"""
Encrypted Credential Vault

Provides secure encryption/decryption of broker credentials using Fernet (AES-128-CBC).
All sensitive data (API keys, tokens, passwords) are encrypted at rest and decrypted on-demand.

Usage:
    vault = Vault.initialize(master_key="your-32-byte-base64-key")
    vault.store("alpaca_key", secret_value)
    secret = vault.retrieve("alpaca_key")

Encryption Details:
- Algorithm: Fernet (symmetric encryption, AES-128-CBC)
- Key Size: 32 bytes (256 bits)
- Format: URL-safe Base64 encoding
- Timestamp Included: Yes (prevents replay attacks)
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64


logger = logging.getLogger(__name__)


class VaultError(Exception):
    """Base exception for vault operations."""
    pass


class VaultInitializationError(VaultError):
    """Raised when vault initialization fails."""
    pass


class VaultEncryptionError(VaultError):
    """Raised when encryption fails."""
    pass


class VaultDecryptionError(VaultError):
    """Raised when decryption fails."""
    pass


class VaultKeyNotFoundError(VaultError):
    """Raised when a key is not found in the vault."""
    pass


class Vault:
    """
    Encrypted credential vault using Fernet (AES-128-CBC).
    
    Attributes:
        master_key (bytes): The encryption key (32 bytes, base64-encoded)
        cipher (Fernet): Fernet cipher instance for encrypt/decrypt
        storage (Dict[str, str]): In-memory storage of encrypted credentials
    """
    
    def __init__(self, master_key: bytes):
        """
        Initialize vault with a master key.
        
        Args:
            master_key (bytes): 32-byte Fernet key (base64-encoded)
            
        Raises:
            VaultInitializationError: If master_key is invalid
        """
        if not master_key or len(master_key) != 44:  # Base64-encoded 32 bytes
            raise VaultInitializationError(
                "Master key must be 44 characters (base64-encoded 32 bytes)"
            )
        
        try:
            self.master_key = master_key
            self.cipher = Fernet(master_key)
            self.storage: Dict[str, str] = {}
            logger.info("Vault initialized successfully")
        except Exception as e:
            raise VaultInitializationError(f"Failed to initialize Fernet cipher: {e}")
    
    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new random master key.
        
        Returns:
            bytes: 32-byte Fernet key (base64-encoded)
        """
        return Fernet.generate_key()
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """
        Derive a Fernet-compatible key from a password using PBKDF2.
        
        Args:
            password (str): Password to derive from
            salt (bytes, optional): Salt for derivation (generated if not provided)
            
        Returns:
            tuple[bytes, bytes]: (derived_key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    @classmethod
    def initialize(cls, master_key: Optional[bytes] = None) -> "Vault":
        """
        Initialize a vault with a master key.
        
        Args:
            master_key (bytes, optional): Existing key. If None, generates new key.
            
        Returns:
            Vault: Initialized vault instance
            
        Raises:
            VaultInitializationError: If initialization fails
        """
        if master_key is None:
            master_key = cls.generate_key()
            logger.info("Generated new master key")
        
        return cls(master_key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext (str): Text to encrypt
            
        Returns:
            str: Encrypted ciphertext (base64-encoded)
            
        Raises:
            VaultEncryptionError: If encryption fails
        """
        if not plaintext:
            raise VaultEncryptionError("Cannot encrypt empty plaintext")
        
        try:
            ciphertext = self.cipher.encrypt(plaintext.encode()).decode()
            logger.debug(f"Encrypted {len(plaintext)} bytes")
            return ciphertext
        except Exception as e:
            raise VaultEncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string.
        
        Args:
            ciphertext (str): Encrypted text to decrypt
            
        Returns:
            str: Decrypted plaintext
            
        Raises:
            VaultDecryptionError: If decryption fails or ciphertext is invalid
        """
        if not ciphertext:
            raise VaultDecryptionError("Cannot decrypt empty ciphertext")
        
        try:
            plaintext = self.cipher.decrypt(ciphertext.encode()).decode()
            logger.debug(f"Decrypted {len(ciphertext)} bytes")
            return plaintext
        except InvalidToken:
            raise VaultDecryptionError("Invalid or tampered ciphertext (InvalidToken)")
        except Exception as e:
            raise VaultDecryptionError(f"Decryption failed: {e}")
    
    def store(self, key: str, secret: str) -> None:
        """
        Store a secret in the vault (encrypted).
        
        Args:
            key (str): Name/ID of the secret
            secret (str): Secret value to store
            
        Raises:
            VaultEncryptionError: If encryption fails
        """
        if not key or not secret:
            raise VaultEncryptionError("Key and secret cannot be empty")
        
        try:
            encrypted = self.encrypt(secret)
            self.storage[key] = encrypted
            logger.info(f"Stored secret: {key}")
        except VaultEncryptionError:
            raise
        except Exception as e:
            raise VaultEncryptionError(f"Failed to store secret '{key}': {e}")
    
    def retrieve(self, key: str) -> str:
        """
        Retrieve a secret from the vault (decrypted).
        
        Args:
            key (str): Name/ID of the secret
            
        Returns:
            str: Decrypted secret value
            
        Raises:
            VaultKeyNotFoundError: If key doesn't exist
            VaultDecryptionError: If decryption fails
        """
        if key not in self.storage:
            raise VaultKeyNotFoundError(f"Secret '{key}' not found in vault")
        
        try:
            ciphertext = self.storage[key]
            secret = self.decrypt(ciphertext)
            logger.info(f"Retrieved secret: {key}")
            return secret
        except VaultDecryptionError:
            raise
        except Exception as e:
            raise VaultDecryptionError(f"Failed to retrieve secret '{key}': {e}")
    
    def delete(self, key: str) -> None:
        """
        Delete a secret from the vault.
        
        Args:
            key (str): Name/ID of the secret
            
        Raises:
            VaultKeyNotFoundError: If key doesn't exist
        """
        if key not in self.storage:
            raise VaultKeyNotFoundError(f"Secret '{key}' not found in vault")
        
        del self.storage[key]
        logger.info(f"Deleted secret: {key}")
    
    def exists(self, key: str) -> bool:
        """Check if a secret exists in the vault."""
        return key in self.storage
    
    def list_keys(self) -> list[str]:
        """List all secret keys in the vault."""
        return list(self.storage.keys())
    
    def to_json(self) -> str:
        """
        Export vault storage to JSON (encrypted values only).
        
        Returns:
            str: JSON representation of vault
        """
        return json.dumps(self.storage, indent=2)
    
    def from_json(self, json_data: str) -> None:
        """
        Import vault storage from JSON.
        
        Args:
            json_data (str): JSON representation of vault
            
        Raises:
            VaultError: If import fails
        """
        try:
            imported = json.loads(json_data)
            if not isinstance(imported, dict):
                raise VaultError("Invalid JSON: must be a dictionary")
            self.storage = imported
            logger.info(f"Imported {len(imported)} secrets from JSON")
        except json.JSONDecodeError as e:
            raise VaultError(f"Invalid JSON: {e}")
    
    def clear(self) -> None:
        """Clear all secrets from the vault."""
        self.storage.clear()
        logger.warning("Vault cleared")
    
    def get_storage_size(self) -> int:
        """Return the number of secrets in the vault."""
        return len(self.storage)
