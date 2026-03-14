"""Tests for structured JSON logging."""

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "control-plane" / "api-server"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "data-plane"))


def test_api_structured_log_format():
    from app.structured_log import get_logger

    logger = get_logger("test_component")
    buf = io.StringIO()
    with patch("builtins.print", side_effect=lambda *a, **kw: buf.write(str(a[0]) + "\n")):
        logger.info("hello world")

    line = buf.getvalue().strip()
    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["component"] == "test_component"
    assert data["message"] == "hello world"
    assert "timestamp" in data
    assert "request_id" in data
    print("  PASS: API structured logger outputs valid JSON with required fields")


def test_data_plane_structured_log_format():
    from agent_runner.structured_log import get_logger

    logger = get_logger("runner")
    buf = io.StringIO()
    with patch("builtins.print", side_effect=lambda *a, **kw: buf.write(str(a[0]) + "\n")):
        logger.error("something broke", job_id=42)

    line = buf.getvalue().strip()
    data = json.loads(line)
    assert data["level"] == "ERROR"
    assert data["component"] == "runner"
    assert data["message"] == "something broke"
    assert data["job_id"] == 42
    assert "timestamp" in data
    print("  PASS: Data-plane structured logger outputs valid JSON with extra fields")


def test_structured_log_levels():
    from app.structured_log import get_logger

    logger = get_logger("test")
    buf = io.StringIO()
    with patch("builtins.print", side_effect=lambda *a, **kw: buf.write(str(a[0]) + "\n")):
        logger.info("i")
        logger.error("e")
        logger.warning("w")
        logger.debug("d")

    lines = [json.loads(line) for line in buf.getvalue().strip().split("\n")]
    levels = [entry["level"] for entry in lines]
    assert levels == ["INFO", "ERROR", "WARNING", "DEBUG"]
    print("  PASS: All log levels emit correctly")


if __name__ == "__main__":
    test_api_structured_log_format()
    test_data_plane_structured_log_format()
    test_structured_log_levels()
    print("\nAll structured log tests passed!")
