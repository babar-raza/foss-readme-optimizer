"""Verbatim regex adopted from aspose.org's metrics_schema.py. Masks exact
matches of live secret values before anything is written to evidence.
"""

import re

_SECRET_LIKE_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9]{10,})"
    r"|(ghp_[A-Za-z0-9]{10,})"
    r"|(ghu_[A-Za-z0-9]{10,})"
    r"|(AIzaSy[A-Za-z0-9_-]{10,})"
    r"|(Bearer\s+[A-Za-z0-9._-]{20,})"
    r"|([?&](api_key|token|key|access_token)=[^\s&]{8,})",
    re.IGNORECASE,
)


def redact_secret_like_values(value: str) -> str:
    if not isinstance(value, str):
        return value
    return _SECRET_LIKE_PATTERN.sub("[REDACTED]", value)


def redact(text: str, live_secret_values: list[str] | None = None) -> str:
    """Pattern-based redaction, plus exact-match masking of whatever secret
    values are actually live in this process's environment right now."""
    result = redact_secret_like_values(text)
    for secret in live_secret_values or []:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result
