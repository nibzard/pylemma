"""Trace navigation never mistakes an ordinary project link for public access."""

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from pylemma.machines import Blueprint
from pylemma.trace_links import inspect_link

TRACE = "01a18279f80e04757e90f2b753321bc4"
PROJECT = "https://logfire-eu.pydantic.dev/nibzard/starter-project/"
PUBLIC = "https://logfire-eu.pydantic.dev/public-trace/example"


def test_exact_trace_and_completion_window_without_mutation() -> None:
    data = {"trace_id": TRACE, "created_at": "2026-10-28T12:26:35+00:00"}
    linked = inspect_link(data, PROJECT)
    assert linked["logfire_access"] == "account"
    query = parse_qs(urlsplit(linked["logfire_url"]).query)
    assert query["q"] == [f"trace_id='{TRACE}'"]
    assert query["since"] == ["2026-10-28T11:26:35+00:00"]
    assert query["until"] == ["2026-10-28T13:26:35+00:00"]
    assert "logfire_url" not in data
    old = inspect_link({"trace_id": TRACE}, PROJECT)
    assert parse_qs(urlsplit(old["logfire_url"]).query) == {
        "q": [f"trace_id='{TRACE}'"]
    }


def test_reviewed_public_link_precedes_project_link() -> None:
    assert (
        inspect_link({"trace_id": TRACE}, PROJECT, {TRACE: PUBLIC})["logfire_access"]
        == "public"
    )
    result = inspect_link({"trace_id": TRACE, "public_trace_url": PUBLIC}, PROJECT)
    assert result["logfire_url"] == PUBLIC
    assert result["logfire_access"] == "public"
    result = inspect_link(
        {"trace_id": TRACE, "public_trace_url": "javascript:alert(1)"}, PROJECT
    )
    assert result["logfire_access"] == "account"


@pytest.mark.parametrize(
    "project",
    [
        "javascript:alert(1)",
        "https://example.com/nibzard/project",
        "https://logfire-eu.pydantic.dev.evil.test/a/b",
        "https://logfire-eu.pydantic.dev:443/a/b",
        "https://user@logfire-eu.pydantic.dev/a/b",
        PROJECT + "?token=secret",
        PROJECT + "\n",
        PROJECT + "%20",
    ],
)
def test_bad_project_is_unavailable(project: str) -> None:
    assert inspect_link({"trace_id": TRACE}, project)["logfire_access"] == "unavailable"


def test_missing_or_invalid_trace_does_not_invent_a_link() -> None:
    for trace in (None, "not-a-trace", "' OR true"):
        result = inspect_link({"trace_id": trace}, PROJECT)
        assert result["logfire_url"] is None
        assert result["logfire_access"] == "unavailable"


@pytest.mark.parametrize("public", [False, True])
def test_replay_api_exposes_the_correct_access_mode(
    tmp_path: Path, public: bool
) -> None:
    import logfire
    from fastapi.testclient import TestClient

    from pylemma.machine_store import MachineStore
    from pylemma.web.app import create_app

    class NoBuilder:
        async def generate(self, strategy: str) -> Blueprint:
            raise AssertionError("A replay read must not generate a player.")

        async def close(self) -> None:
            pass

    store = MachineStore(tmp_path / "links.sqlite3")
    identifier = store.replay({"trace_id": TRACE, "result": {}})
    telemetry = logfire.configure(send_to_logfire=False, console=False, local=True)
    app = create_app(
        store,
        NoBuilder(),
        telemetry,
        1,
        logfire_project_url=PROJECT,
        public_trace_urls={TRACE: PUBLIC} if public else {},
    )
    with TestClient(app) as client:
        replay = client.get("/api/replays/" + str(identifier)).json()
        assert replay["logfire_access"] == ("public" if public else "account")
        assert replay["logfire_url"].startswith(PUBLIC if public else PROJECT)
        assert "logfire_url" not in store.read(identifier)


def test_verified_public_span_highlight_preserves_the_shared_url() -> None:
    url = (
        "https://logfire-eu.pydantic.dev/public-trace/"
        "44e57f30-c25a-47fe-b85f-5db1d0604010?spanId=4ed36f7dff63d8fe"
    )
    linked = inspect_link({"trace_id": TRACE}, PROJECT, {TRACE: url})
    assert linked["logfire_access"] == "public"
    assert linked["logfire_url"] == url
    for suffix in (
        "&redirect=https://example.com",
        "&spanId=0000000000000000",
        "#fragment",
    ):
        assert (
            inspect_link({"trace_id": TRACE}, PROJECT, {TRACE: url + suffix})[
                "logfire_access"
            ]
            == "account"
        )
