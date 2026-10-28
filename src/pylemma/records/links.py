"""Conservative reviewed-link validation; this module never fetches a URL."""

from urllib.parse import urlsplit

LOGFIRE_HOSTS = frozenset(
    {"logfire.pydantic.dev", "logfire-us.pydantic.dev", "logfire-eu.pydantic.dev"}
)


def validate_public_url(value: str) -> str:
    """Accept exact HTTPS hosts without credentials, ports, or redirect parameters."""
    if len(value) > 2048 or any(ord(char) <= 32 or ord(char) >= 127 for char in value):
        raise ValueError("Invalid trace URL. Use the reviewed ASCII HTTPS link.")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc not in LOGFIRE_HOSTS
        or not parsed.path.startswith("/")
        or parsed.path == "/"
        or "\\" in value
        or "%" in value
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Invalid trace URL. Use an allowed Logfire host without URL parameters."
        )
    return value
