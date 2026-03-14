"""Tests for request context (X-Request-ID via contextvars)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "control-plane" / "api-server"))

from app.request_context import get_request_id, set_request_id


def test_default_empty():
    assert get_request_id() == ""
    print("  PASS: Default request_id is empty string")


def test_set_and_get():
    set_request_id("abc-123")
    assert get_request_id() == "abc-123"
    # Reset
    set_request_id("")
    print("  PASS: set/get request_id round-trips")


def test_token_reset():
    set_request_id("first")
    assert get_request_id() == "first"
    set_request_id("second")
    assert get_request_id() == "second"
    set_request_id("")
    print("  PASS: request_id can be overwritten")


if __name__ == "__main__":
    test_default_empty()
    test_set_and_get()
    test_token_reset()
    print("\nAll request tracing tests passed!")
