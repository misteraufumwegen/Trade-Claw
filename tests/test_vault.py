"""
Unit tests for the Encrypted Credential Vault.

Tests cover:
- Key generation
- Key derivation from password
- Encryption/decryption
- Store/retrieve operations
- Error handling
- JSON import/export
"""

import json

import pytest

from app.vault import (
    Vault,
    VaultDecryptionError,
    VaultEncryptionError,
    VaultError,
    VaultInitializationError,
    VaultKeyNotFoundError,
)


class TestVaultKeyGeneration:
    """Test vault key generation and initialization."""

    def test_generate_key(self):
        """Test generating a new random key."""
        key1 = Vault.generate_key()
        key2 = Vault.generate_key()

        assert isinstance(key1, bytes)
        assert isinstance(key2, bytes)
        assert len(key1) == 44  # Base64-encoded 32 bytes
        assert len(key2) == 44
        assert key1 != key2  # Should be different

    def test_initialize_with_key(self):
        """Test initializing vault with a provided key."""
        key = Vault.generate_key()
        vault = Vault.initialize(master_key=key)

        assert vault is not None
        assert vault.master_key == key
        # Storage is now a pluggable backend; use the public API.
        assert vault.get_storage_size() == 0

    def test_initialize_without_key(self):
        """Test initializing vault without a key (auto-generates)."""
        vault = Vault.initialize()

        assert vault is not None
        assert len(vault.master_key) == 44

    def test_initialize_with_invalid_key(self):
        """Test initializing vault with an invalid key."""
        with pytest.raises(VaultInitializationError):
            Vault.initialize(master_key=b"short")

        with pytest.raises(VaultInitializationError):
            Vault.initialize(master_key=b"")

    def test_derive_key_from_password(self):
        """Test deriving a key from a password."""
        password = "mysecurepassword123"
        key, salt = Vault.derive_key_from_password(password)

        assert isinstance(key, bytes)
        assert isinstance(salt, bytes)
        assert len(key) == 44  # Fernet key size
        assert len(salt) == 16  # Default salt size

    def test_derive_key_consistent(self):
        """Test that deriving from the same password + salt gives the same key."""
        password = "mysecurepassword123"
        key1, salt = Vault.derive_key_from_password(password)
        key2, _ = Vault.derive_key_from_password(password, salt=salt)

        assert key1 == key2  # Same password + salt = same key


class TestVaultEncryptDecrypt:
    """Test encryption and decryption."""

    @pytest.fixture
    def vault(self):
        """Create a vault instance for testing."""
        return Vault.initialize()

    def test_encrypt_decrypt_round_trip(self, vault):
        """Test that encrypt then decrypt returns original value."""
        secret = "my-secret-api-key-12345"
        encrypted = vault.encrypt(secret)
        decrypted = vault.decrypt(encrypted)

        assert encrypted != secret  # Ciphertext is different
        assert decrypted == secret  # Decrypted matches original

    def test_encrypt_produces_different_ciphertext(self, vault):
        """Test that encrypting the same value twice produces different ciphertexts."""
        secret = "api-key"
        encrypted1 = vault.encrypt(secret)
        encrypted2 = vault.encrypt(secret)

        # Due to Fernet timestamp, should be different
        assert encrypted1 != encrypted2
        assert vault.decrypt(encrypted1) == secret
        assert vault.decrypt(encrypted2) == secret

    def test_encrypt_empty_string_fails(self, vault):
        """Test that encrypting empty string fails."""
        with pytest.raises(VaultEncryptionError):
            vault.encrypt("")

    def test_decrypt_empty_string_fails(self, vault):
        """Test that decrypting empty string fails."""
        with pytest.raises(VaultDecryptionError):
            vault.decrypt("")

    def test_decrypt_invalid_ciphertext(self, vault):
        """Test that decrypting invalid ciphertext fails."""
        with pytest.raises(VaultDecryptionError):
            vault.decrypt("invalid-ciphertext-data")

    def test_decrypt_tampered_ciphertext(self, vault):
        """Test that tampered ciphertext is detected."""
        secret = "original-secret"
        encrypted = vault.encrypt(secret)
        tampered = encrypted[:-10] + "0000000000"

        with pytest.raises(VaultDecryptionError):
            vault.decrypt(tampered)

    def test_decrypt_with_wrong_key(self):
        """Test that decrypting with wrong key fails."""
        vault1 = Vault.initialize()
        vault2 = Vault.initialize()  # Different key

        secret = "api-key"
        encrypted = vault1.encrypt(secret)

        with pytest.raises(VaultDecryptionError):
            vault2.decrypt(encrypted)


class TestVaultStoreRetrieve:
    """Test store and retrieve operations."""

    @pytest.fixture
    def vault(self):
        """Create a vault instance for testing."""
        return Vault.initialize()

    def test_store_and_retrieve(self, vault):
        """Test storing and retrieving a secret."""
        vault.store("alpaca_key", "abc123xyz789")
        retrieved = vault.retrieve("alpaca_key")

        assert retrieved == "abc123xyz789"

    def test_store_multiple_secrets(self, vault):
        """Test storing multiple secrets."""
        vault.store("alpaca_key", "alpaca-secret-123")
        vault.store("oanda_token", "oanda-token-456")
        vault.store("reddit_api", "reddit-api-789")

        assert vault.retrieve("alpaca_key") == "alpaca-secret-123"
        assert vault.retrieve("oanda_token") == "oanda-token-456"
        assert vault.retrieve("reddit_api") == "reddit-api-789"

    def test_retrieve_nonexistent_key(self, vault):
        """Test retrieving a key that doesn't exist."""
        with pytest.raises(VaultKeyNotFoundError):
            vault.retrieve("nonexistent")

    def test_store_empty_secret_fails(self, vault):
        """Test that storing empty secret fails."""
        with pytest.raises(VaultEncryptionError):
            vault.store("key", "")

    def test_store_empty_key_fails(self, vault):
        """Test that storing with empty key fails."""
        with pytest.raises(VaultEncryptionError):
            vault.store("", "secret")

    def test_exists_checks_key(self, vault):
        """Test the exists() method."""
        vault.store("key1", "secret1")

        assert vault.exists("key1") is True
        assert vault.exists("key2") is False

    def test_list_keys(self, vault):
        """Test listing all keys."""
        vault.store("key1", "secret1")
        vault.store("key2", "secret2")
        vault.store("key3", "secret3")

        keys = vault.list_keys()
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys


class TestVaultDelete:
    """Test delete operations."""

    @pytest.fixture
    def vault(self):
        """Create a vault instance for testing."""
        return Vault.initialize()

    def test_delete_secret(self, vault):
        """Test deleting a secret."""
        vault.store("key1", "secret1")
        assert vault.exists("key1") is True

        vault.delete("key1")
        assert vault.exists("key1") is False

    def test_delete_nonexistent_key(self, vault):
        """Test deleting a key that doesn't exist."""
        with pytest.raises(VaultKeyNotFoundError):
            vault.delete("nonexistent")

    def test_clear_vault(self, vault):
        """Test clearing the entire vault."""
        vault.store("key1", "secret1")
        vault.store("key2", "secret2")

        assert vault.get_storage_size() == 2
        vault.clear()
        assert vault.get_storage_size() == 0


class TestVaultJSON:
    """Test JSON export and import."""

    @pytest.fixture
    def vault(self):
        """Create a vault instance for testing."""
        return Vault.initialize()

    def test_to_json(self, vault):
        """Test exporting vault to JSON."""
        vault.store("key1", "secret1")
        vault.store("key2", "secret2")

        json_str = vault.to_json()
        data = json.loads(json_str)

        assert isinstance(data, dict)
        assert len(data) == 2
        assert "key1" in data
        assert "key2" in data

    def test_from_json(self, vault):
        """Test importing vault from JSON."""
        json_str = '{"key1": "encrypted1", "key2": "encrypted2"}'
        vault.from_json(json_str)

        assert vault.get_storage_size() == 2
        assert vault.exists("key1")
        assert vault.exists("key2")

    def test_from_json_invalid(self, vault):
        """Test importing invalid JSON."""
        with pytest.raises(VaultError):
            vault.from_json("invalid json")

        with pytest.raises(VaultError):
            vault.from_json('["array", "not", "dict"]')

    def test_json_round_trip(self, vault):
        """Test JSON export/import round trip."""
        vault.store("key1", "secret1")
        vault.store("key2", "secret2")

        json_str = vault.to_json()

        vault2 = Vault.initialize()
        vault2.from_json(json_str)

        # Note: Can't decrypt without same key, but storage should match
        assert vault2.get_storage_size() == 2
        assert vault2.exists("key1")
        assert vault2.exists("key2")


class TestVaultSize:
    """Test vault size operations."""

    @pytest.fixture
    def vault(self):
        """Create a vault instance for testing."""
        return Vault.initialize()

    def test_get_storage_size(self, vault):
        """Test getting vault size."""
        assert vault.get_storage_size() == 0

        vault.store("key1", "secret1")
        assert vault.get_storage_size() == 1

        vault.store("key2", "secret2")
        assert vault.get_storage_size() == 2

        vault.delete("key1")
        assert vault.get_storage_size() == 1

        vault.clear()
        assert vault.get_storage_size() == 0


class TestVaultIntegration:
    """Integration tests for realistic broker credential scenarios."""

    def test_broker_credentials_scenario(self):
        """Test storing multiple broker credentials."""
        vault = Vault.initialize()

        # Store broker credentials
        vault.store("alpaca_api_key", "PKABC123DEF456GHI789")
        vault.store("alpaca_secret_key", "SecretKeyHere123456789")
        vault.store("oanda_token", "AuthTokenHere123456789")
        vault.store("oanda_account_id", "123456789")

        # Retrieve and verify
        assert vault.retrieve("alpaca_api_key") == "PKABC123DEF456GHI789"
        assert vault.retrieve("alpaca_secret_key") == "SecretKeyHere123456789"
        assert vault.retrieve("oanda_token") == "AuthTokenHere123456789"
        assert vault.retrieve("oanda_account_id") == "123456789"

    def test_vault_with_special_characters(self):
        """Test vault with secrets containing special characters."""
        vault = Vault.initialize()

        special_secret = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        vault.store("special", special_secret)

        assert vault.retrieve("special") == special_secret

    def test_vault_with_long_secret(self):
        """Test vault with very long secret."""
        vault = Vault.initialize()

        long_secret = "x" * 10000  # 10KB secret
        vault.store("long", long_secret)

        assert vault.retrieve("long") == long_secret
        assert len(vault.retrieve("long")) == 10000
