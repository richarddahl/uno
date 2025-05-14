import pytest
from uno.config import SecureValue, SecureValueHandling

class TestSecureValueKDF:
    def test_kdf_params_round_trip(self, setup_secure_config):
        # Use custom KDF params
        kdf_params = {"algorithm": "sha256", "iterations": 123456, "length": 32}
        val = SecureValue("topsecret", handling=SecureValueHandling.ENCRYPT, kdf_params=kdf_params)
        assert val._kdf_params == kdf_params
        # Value should decrypt correctly and preserve KDF params
        assert val.get_value() == "topsecret"
        # After decrypt, KDF params should be preserved
        assert val._kdf_params == kdf_params

    def test_backward_compatibility(self, setup_secure_config):
        # Simulate legacy value (no kdf_params in metadata)
        val = SecureValue("legacy", handling=SecureValueHandling.ENCRYPT)
        val._kdf_params = {"algorithm": "sha256", "iterations": 10000, "length": 32}
        val._encrypt()
        # Remove kdf_params from metadata (simulate old value)
        import json
        import base64
        from cryptography.fernet import Fernet
        fernet, _ = val._get_fernet()
        decrypted = fernet.decrypt(val._value)
        meta = json.loads(decrypted.decode("utf-8"))
        meta.pop("kdf_params", None)
        val._value = fernet.encrypt(json.dumps(meta).encode("utf-8"))
        # Should still decrypt
        assert val.get_value() == "legacy"

    def test_rotate_kdf(self, setup_secure_config):
        val = SecureValue("rotate-me", handling=SecureValueHandling.ENCRYPT)
        old_params = val._kdf_params.copy()
        new_params = {"algorithm": "sha256", "iterations": 999999, "length": 32}
        val.rotate_kdf(new_params)
        # KDF params should be updated and value still decrypts
        assert val._kdf_params == new_params
        assert val.get_value() == "rotate-me"
        # Should not match old params
        assert val._kdf_params != old_params

    def test_rotate_kdf_noop_on_mask(self, setup_secure_config):
        val = SecureValue("plain", handling=SecureValueHandling.MASK)
        val.rotate_kdf({"algorithm": "sha256", "iterations": 1, "length": 32})
        # Should be a no-op and not error
        assert val.get_value() == "plain"
