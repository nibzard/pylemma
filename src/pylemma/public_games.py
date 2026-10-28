"""Small public read models. Missing consent always means an unlisted record."""

from datetime import UTC, datetime
from typing import Any


def entry(identifier: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """List only complete games whose participating visitors permit discovery."""
    kind = data.get("kind")
    result = data.get("result", {})
    suite = result.get("suite_version")
    rounds_per_match = 20 if kind == "arena" and suite == "arena-v2" else 10
    if kind in ("tournament", "arena"):
        machines = [data.get("machine", {})]
        matches = result.get("matches", [])
        if len(matches) != (10 if kind == "arena" else 3) or any(
            len(match.get("rounds", [])) != rounds_per_match for match in matches
        ):
            return None
        suites = ("arena-v1", "arena-v2") if kind == "arena" else ("trust-v1",)
        if result.get("rules_version") != "pd-v1" or suite not in suites:
            return None
        scores = [result.get("total")]
    elif kind == "challenge":
        machines = data.get("machines", [])
        if len(machines) != 2 or len(result.get("rounds", [])) != 10:
            return None
        scores = result.get("totals", [])
        if len(scores) != 2:
            return None
    else:
        return None
    if (
        not machines
        or any(m.get("public_listing") is not True for m in machines)
        or any(
            type(score) is not int
            or not 0 <= score <= (50 * rounds_per_match if kind == "arena" else 150)
            for score in scores
        )
    ):
        return None
    return {
        "replay_id": identifier,
        "kind": kind,
        "players": [{"id": m["id"], "name": m["name"]} for m in machines],
        "scores": scores,
        "created_at": data.get("created_at"),
        "suite_version": suite,
        "rounds_per_match": rounds_per_match,
    }


def page(
    entries: list[dict[str, Any]], ranked: bool, offset: int, limit: int
) -> dict[str, Any]:
    """Use competition ranks: equal scores share a rank, followed by a gap."""
    rows = [dict(row) for row in entries if not ranked or row["kind"] == "tournament"]
    if ranked:
        rows.sort(key=lambda row: (-row["scores"][0], row["replay_id"]))
        rank = 0
        previous = None
        for index, row in enumerate(rows):
            if row["scores"][0] != previous:
                rank = index + 1
            previous = row["scores"][0]
            row["rank"] = rank
    else:

        def order(row: dict[str, Any]) -> tuple[float, str]:
            stamp = row.get("created_at")
            timestamp = datetime.fromisoformat(stamp).timestamp() if stamp else 0.0
            return timestamp, row["replay_id"]

        rows.sort(key=order, reverse=True)
    end = offset + limit
    return {
        "entries": rows[offset:end],
        "total": len(rows),
        "next_offset": end if end < len(rows) else None,
    }


def timestamp() -> str:
    """Use an aware UTC completion time for newly saved replays."""
    return datetime.now(UTC).isoformat()
