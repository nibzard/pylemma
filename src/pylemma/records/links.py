"""Conservative reviewed-link validation; this module never fetches a URL."""

import re
from urllib.parse import parse_qsl, urlsplit

LOGFIRE_HOSTS = frozenset(
    {"logfire.pydantic.dev", "logfire-us.pydantic.dev", "logfire-eu.pydantic.dev"}
)


def validate_public_url(value: str) -> str:
    """Accept exact HTTPS hosts and verified public-trace span highlights."""
    if len(value) > 2048 or any(ord(char) <= 32 or ord(char) >= 127 for char in value):
        raise ValueError("Invalid trace URL. Use the reviewed ASCII HTTPS link.")
    parsed = urlsplit(value)
    highlight = (
        re.fullmatch(
            r"/public-trace/[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}",
            parsed.path,
        )
        and len(parse_qsl(parsed.query, keep_blank_values=True)) == 1
        and re.fullmatch(r"spanId=[a-fA-F0-9]{16}", parsed.query)
    )
    if (
        parsed.scheme != "https"
        or parsed.netloc not in LOGFIRE_HOSTS
        or not parsed.path.startswith("/")
        or parsed.path == "/"
        or "\\" in value
        or "%" in value
        or (parsed.query and not highlight)
        or parsed.fragment
    ):
        raise ValueError(
            "Invalid trace URL. Use an allowed Logfire host "
            "and a reviewed public trace link."
        )
    return value
