"""Input sanitization before sending data to LLM."""

import re

# Patterns to detect and redact sensitive data
PATTERNS = [
    # API keys and tokens (generic patterns)
    (re.compile(r'(?i)(api[_-]?key|token|secret|password|credential)[\s]*[=:]\s*["\']?([A-Za-z0-9_\-\.]{20,})["\']?'), r'\1=***REDACTED***'),
    # AWS access keys
    (re.compile(r'AKIA[0-9A-Z]{16}'), '***AWS_KEY_REDACTED***'),
    # Generic long hex/base64 secrets
    (re.compile(r'(?i)(bearer|authorization)\s+[A-Za-z0-9_\-\.]{30,}'), r'\1 ***REDACTED***'),
    # Private keys
    (re.compile(r'-----BEGIN\s+\w+\s+PRIVATE\s+KEY-----[\s\S]*?-----END\s+\w+\s+PRIVATE\s+KEY-----'), '***PRIVATE_KEY_REDACTED***'),
    # Connection strings with passwords
    (re.compile(r'(://\w+:)[^@]+(@)'), r'\1***@'),
]


def sanitize_for_llm(text: str) -> str:
    """Remove sensitive data patterns from text before sending to LLM."""
    result = text
    for pattern, replacement in PATTERNS:
        result = pattern.sub(replacement, result)
    return result
