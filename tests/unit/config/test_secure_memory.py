"""Tests for secure memory handling and context manager support in SecureValue."""

import pytest
from uno.config import SecureValue, SecureValueHandling

class TestSecureValueMemory:
    def test_clear_overwrites_value(self, setup_secure_config):
        val = SecureValue("sensitive", handling=SecureValueHandling.MASK)
        orig = val._value
        val.clear()
        # After clear, value should be zeroed or empty
        assert val._value == "\x00" * len(orig)
        assert val._original_value is None

    def test_bytes_type_not_supported(self, setup_secure_config):
        with pytest.raises(TypeError):
            SecureValue(b"secret-bytes", handling=SecureValueHandling.MASK)

    def test_clear_overwrites_salt(self, setup_secure_config):
        val = SecureValue("test", handling=SecureValueHandling.MASK)
        orig_salt = val._salt
        val.clear()
        assert val._salt == b"\x00" * len(orig_salt)

    def test_context_manager_clears(self, setup_secure_config):
        val = SecureValue("secret", handling=SecureValueHandling.MASK)
        with val as v:
            assert v.get_value() == "secret"
        # After context, value should be cleared
        assert v._value == "\x00" * len("secret")
        assert v._original_value is None

    def test_context_manager_usage(self, setup_secure_config):
        with SecureValue("abc", handling=SecureValueHandling.MASK) as val:
            assert val.get_value() == "abc"
        assert val._value == "\x00" * len("abc")
        assert val._original_value is None

    def test_clear_idempotent(self, setup_secure_config):
        val = SecureValue("test", handling=SecureValueHandling.MASK)
        val.clear()
        val.clear()  # Should not error
        assert val._original_value is None

    def test_clear_on_del(monkeypatch, setup_secure_config):
        # This test ensures __del__ calls clear (best effort)
        cleared = {}
        class Dummy(SecureValue[str]):
            def clear(self_inner):
                cleared["called"] = True
        d = Dummy("x", handling=SecureValueHandling.MASK)
        d.__del__()
        assert cleared["called"]
