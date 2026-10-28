"""Replay links use verified Logfire UI filters and explicit access labels."""

import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlsplit

from pylemma.records.links import LOGFIRE_HOSTS, validate_public_url

TRACE = re.compile(r"^[a-fA-F0-9]{32}$")
PROJECT_PATH = re.compile(r"^/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/?$")


def inspect_link(
    data: dict[str, Any],
    project_url: str | None,
    public_urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Decorate a replay without changing stored scores or claiming public access."""
    result = {**data, "logfire_url": None, "logfire_access": "unavailable"}
    trace = data.get("trace_id")
    if not isinstance(trace, str) or not TRACE.fullmatch(trace):
        return result
    public = data.get("public_trace_url") or (public_urls or {}).get(trace)
    if isinstance(public, str):
        try:
            result.update(
                logfire_url=validate_public_url(public), logfire_access="public"
            )
            return result
        except ValueError:
            pass
    if (
        not project_url
        or len(project_url) > 2048
        or any(ord(char) <= 32 or ord(char) >= 127 for char in project_url)
        or "%" in project_url
        or "\\" in project_url
    ):
        return result
    parsed = urlsplit(project_url)
    if (
        parsed.scheme != "https"
        or parsed.netloc not in LOGFIRE_HOSTS
        or not PROJECT_PATH.fullmatch(parsed.path)
        or parsed.query
        or parsed.fragment
    ):
        return result
    query = {"q": f"trace_id='{trace}'"}
    try:
        stamp = datetime.fromisoformat(data["created_at"])
        if stamp.utcoffset() is not None:
            query.update(
                since=(stamp - timedelta(hours=1)).isoformat(),
                until=(stamp + timedelta(hours=1)).isoformat(),
            )
    except (KeyError, TypeError, ValueError, OverflowError):
        pass
    result.update(
        logfire_url=project_url.rstrip("/") + "/?" + urlencode(query),
        logfire_access="account",
    )
    return result
