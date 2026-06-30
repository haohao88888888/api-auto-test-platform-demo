import copy
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


MASK = "[REDACTED]"
SENSITIVE_KEYS = ("authorization", "token", "password", "secret", "api_key", "apikey")

PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", flags=re.IGNORECASE),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b"),
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\b\d{17}[\dXx]\b"),
]


def is_sensitive_key(key):
    normalized = str(key).lower().replace("-", "_")
    return any(item in normalized for item in SENSITIVE_KEYS)


def redact_text(value):
    redacted = str(value)
    for pattern in PATTERNS:
        redacted = pattern.sub(MASK, redacted)
    return redacted


def redact_url(url):
    if not url:
        return url

    parts = urlsplit(str(url))
    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        query_items.append((key, MASK if is_sensitive_key(key) else redact_text(value)))

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            redact_text(parts.path),
            urlencode(query_items),
            parts.fragment,
        )
    )


def redact_value(value, key=None):
    if is_sensitive_key(key or ""):
        return MASK

    if isinstance(value, dict):
        return {item_key: redact_value(item_value, item_key) for item_key, item_value in value.items()}

    if isinstance(value, list):
        return [redact_value(item) for item in value]

    if isinstance(value, str):
        return redact_text(value)

    return value


def redact_result(result):
    redacted = redact_value(copy.deepcopy(result))
    if isinstance(redacted, dict) and redacted.get("url"):
        redacted["url"] = redact_url(redacted["url"])
    return redacted


def redact_results(results):
    return [redact_result(result) for result in results]
