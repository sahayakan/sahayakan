"""Unit tests for input sanitization."""

import sys

sys.path.insert(0, "data-plane")

from agent_runner.sanitize import sanitize_for_llm


def test_redacts_api_keys():
    text = 'Set api_key="sk-1234567890abcdef1234567890abcdef" in config'
    result = sanitize_for_llm(text)
    assert "sk-1234567890" not in result
    assert "REDACTED" in result


def test_redacts_aws_keys():
    text = "AWS key: AKIAIOSFODNN7EXAMPLE"
    result = sanitize_for_llm(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in result


def test_redacts_bearer_tokens():
    text = "Authorization Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.long.token"
    result = sanitize_for_llm(text)
    assert "eyJhbGci" not in result


def test_redacts_connection_strings():
    text = "postgres://user:secretpass123@host:5432/db"
    result = sanitize_for_llm(text)
    assert "secretpass123" not in result


def test_redacts_private_keys():
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpA...\n-----END RSA PRIVATE KEY-----"
    result = sanitize_for_llm(text)
    assert "MIIEpA" not in result


def test_preserves_normal_text():
    text = "This is a normal GitHub issue about authentication timeout."
    result = sanitize_for_llm(text)
    assert result == text


if __name__ == "__main__":
    test_redacts_api_keys()
    test_redacts_aws_keys()
    test_redacts_bearer_tokens()
    test_redacts_connection_strings()
    test_redacts_private_keys()
    test_preserves_normal_text()
    print("All sanitization tests passed!")
