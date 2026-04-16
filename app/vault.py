"""
Encrypted Credential Vault

Provides secure encryption/decryption of broker credentials using Fernet
(AES-128-CBC + HMAC-SHA256). All sensitive data (API keys, tokens, passwords)
is encrypted at rest and only decrypted on demand.

Storage backends:
- ``InMemoryStorage``     — RAM only; for tests.
- ``FileStorage``         — JSON file; easy for single-machine dev setups.
- ``DatabaseStorage``     — SQLAlchemy-backed table; recommended for prod.

Usage:
    from app.vault import Vault, DatabaseStorage

    vault = Vault(master_key=os.environb[b"ENCRYPTION_KEY"],
                  storage=DatabaseStorage(session))
    vault.store("alpaca_key", "super-secret")
    print(vault.retrieve("alpaca_key"))

Encryption details:
- Algorithm:  Fernet (AES-128-CBC + HMAC-SHA256)
- Key size:   32 bytes (base64-encoded to 44 chars)
- KDF:        PBKDF2-HMAC-SHA256, 600 000 iterations (OWASP 2023+, M4).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# OWASP 2023+ recommendation for PBKDF2-HMAC-SHA256 (security review M4).
PBKDF2_ITERATIONS = 600_000


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


# ---------------------------------------------------------------------------
# Storage backends
# ---------------------------------------------------------------------------


@runtime_checkable
class VaultStorage(Protocol):
    """Interface every storage backend implements (C3)."""

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, ciphertext: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def keys(self) -> Iterable[str]: ...
    def clear(self) -> None: ...


class InMemoryStorage:
    """RAM-only backend. Useful for tests. Data is lost on restart."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, ciphertext: str) -> None:
        with self._lock:
            self._data[key] = ciphertext

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def keys(self) -> Iterable[str]:
        with self._lock:
            return list(self._data.keys())

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class FileStorage:
    """Simple JSON file backend. Good for single-machine deployments."""

    def __init__(self, path: str | os.PathLike) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write({})

    def _read(self) -> dict[str, str]:
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict[str, str]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        # chmod 0600 — only the owner can read.
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.path)

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._read().get(key)

    def set(self, key: str, ciphertext: str) -> None:
        with self._lock:
            data = self._read()
            data[key] = ciphertext
            self._write(data)

    def delete(self, key: str) -> None:
        with self._lock:
            data = self._read()
            data.pop(key, None)
            self._write(data)

    def keys(self) -> Iterable[str]:
        with self._lock:
            return list(self._read().keys())

    def clear(self) -> None:
        with self._lock:
            self._write({})


class DatabaseStorage:
    """
    SQLAlchemy-backed storage. Uses the ``vault_secrets`` table defined in
    ``app.db.models``. The encrypted blob column stores Fernet-encrypted text.

    Safe to share across threads — each operation runs in its own transaction.
    """

    def __init__(self, session_factory) -> None:
        """
        Args:
            session_factory: a callable that returns a new SQLAlchemy Session,
                e.g. ``SessionLocal`` from ``app.db.session``.
        """
        self._session_factory = session_factory

    def _session(self):
        # Defer import to break a potential circular dependency at module load.
        sess = self._session_factory()
        return sess

    def get(self, key: str) -> str | None:
        from app.db.models import VaultSecret  # local import — see above

        sess = self._session()
        try:
            row = sess.query(VaultSecret).filter(VaultSecret.key == key).first()
            return row.ciphertext if row else None
        finally:
            sess.close()

    def set(self, key: str, ciphertext: str) -> None:
        from app.db.models import VaultSecret

        sess = self._session()
        try:
            row = sess.query(VaultSecret).filter(VaultSecret.key == key).first()
            if row is None:
                row = VaultSecret(key=key, ciphertext=ciphertext)
                sess.add(row)
            else:
                row.ciphertext = ciphertext
            sess.commit()
        finally:
            sess.close()

    def delete(self, key: str) -> None:
        from app.db.models import VaultSecret

        sess = self._session()
        try:
            sess.query(VaultSecret).filter(VaultSecret.key == key).delete()
            sess.commit()
        finally:
            sess.close()

    def keys(self) -> Iterable[str]:
        from app.db.models import VaultSecret

        sess = self._session()
        try:
            return [k for (k,) in sess.query(VaultSecret.key).all()]
        finally:
            sess.close()

    def clear(self) -> None:
        from app.db.models import VaultSecret

        sess = self._session()
        try:
            sess.query(VaultSecret).delete()
            sess.commit()
        finally:
            sess.close()


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------


class Vault:
    """
    Encrypted credential vault using Fernet (AES-128-CBC + HMAC-SHA256).

    Attributes:
        master_key (bytes): The encryption key (32 bytes, base64-encoded)
        cipher (Fernet):    Fernet cipher instance for encrypt/decrypt
        storage (VaultStorage): Pluggable storage backend (C3).
    """

    def __init__(self, master_key: bytes, storage: VaultStorage | None = None):
        """
        Initialise the vault with a master key.

        Args:
            master_key (bytes): 32-byte Fernet key (base64-encoded)
            storage (VaultStorage): Backend implementing get/set/delete/keys/clear.
                Defaults to ``InMemoryStorage`` for backwards compatibility.

        Raises:
            VaultInitializationError: If master_key is invalid.
        """
        if not master_key or len(master_key) != 44:  # Base64-encoded 32 bytes
            raise VaultInitializationError(
                "Master key must be 44 characters (base64-encoded 32 bytes)"
            )

        try:
            self.master_key = master_key
            self.cipher = Fernet(master_key)
            self.storage: VaultStorage = storage or InMemoryStorage()
            logger.info("Vault initialised (backend=%s)", type(self.storage).__name__)
        except Exception as e:
            raise VaultInitializationError(f"Failed to initialise Fernet cipher: {e}") from e

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new random master key.

        Returns:
            bytes: 32-byte Fernet key (base64-encoded)
        """
        return Fernet.generate_key()

    @staticmethod
    def derive_key_from_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
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
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend(),
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt

    @classmethod
    def initialize(cls, master_key: bytes | None = None) -> Vault:
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
            raise VaultEncryptionError(f"Encryption failed: {e}") from e

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
            raise VaultDecryptionError("Invalid or tampered ciphertext (InvalidToken)") from None
        except Exception as e:
            raise VaultDecryptionError(f"Decryption failed: {e}") from e

    def store(self, key: str, secret: str) -> None:
        """Encrypt ``secret`` and store it under ``key``."""
        if not key or not secret:
            raise VaultEncryptionError("Key and secret cannot be empty")

        try:
            encrypted = self.encrypt(secret)
            self.storage.set(key, encrypted)
            logger.info("Stored secret: %s", key)
        except VaultEncryptionError:
            raise
        except Exception as e:  # pragma: no cover - storage-specific
            raise VaultEncryptionError(f"Failed to store secret '{key}': {e}") from e

    def retrieve(self, key: str) -> str:
        """Decrypt and return the secret stored under ``key``."""
        ciphertext = self.storage.get(key)
        if ciphertext is None:
            raise VaultKeyNotFoundError(f"Secret '{key}' not found in vault")

        try:
            secret = self.decrypt(ciphertext)
            logger.debug("Retrieved secret: %s", key)
            return secret
        except VaultDecryptionError:
            raise
        except Exception as e:  # pragma: no cover
            raise VaultDecryptionError(f"Failed to retrieve secret '{key}': {e}") from e

    def delete(self, key: str) -> None:
        """Delete ``key`` from the vault."""
        if self.storage.get(key) is None:
            raise VaultKeyNotFoundError(f"Secret '{key}' not found in vault")
        self.storage.delete(key)
        logger.info("Deleted secret: %s", key)

    def exists(self, key: str) -> bool:
        """Return True if a secret exists for ``key``."""
        return self.storage.get(key) is not None

    def list_keys(self) -> list[str]:
        """Return all secret keys currently stored."""
        return list(self.storage.keys())

    def clear(self) -> None:
        """Remove every secret from the vault."""
        self.storage.clear()
        logger.warning("Vault cleared")

    def get_storage_size(self) -> int:
        """Return the number of secrets currently in the vault."""
        return len(list(self.storage.keys()))

    # -- Backward-compatible JSON export/import helpers ---------------------
    # (they operate on the CIPHERTEXTS already stored in the backend — they
    # never expose plaintext).

    def to_json(self) -> str:
        """Export ``{key: ciphertext}`` as JSON. Plaintext is never serialised."""
        return json.dumps(
            {k: self.storage.get(k) or "" for k in self.storage.keys()},
            indent=2,
        )

    def from_json(self, json_data: str) -> None:
        """Replace vault contents with ``{key: ciphertext}`` from JSON."""
        try:
            imported = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise VaultError(f"Invalid JSON: {e}") from e
        if not isinstance(imported, dict):
            raise VaultError("Invalid JSON: must be a mapping of key → ciphertext")

        self.storage.clear()
        for key, ciphertext in imported.items():
            if not isinstance(ciphertext, str):
                raise VaultError(f"Invalid value for key '{key}': must be a string")
            self.storage.set(key, ciphertext)
        logger.info("Imported %d secrets from JSON", len(imported))
