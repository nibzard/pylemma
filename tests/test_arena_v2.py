"""The new fixed arena cannot silently change historical results."""

from pylemma.machines import Machine, Sandbox, arena, arena_presets, play, presets
from pylemma.public_games import entry


def test_fixed_suite_scores_and_round_counts() -> None:
    sandbox = Sandbox()
    try:
        fixed = arena_presets()
        expected = {
            "The Optimist": 501,
            "The Mirror": 517,
            "The Second Chance": 519,
            "The Rebuilder": 509,
        }
        for blueprint in fixed:
            if blueprint.summary not in expected:
                continue
            machine = Machine.create(
                "Test",
                "Rules",
                blueprint,
                arena_version="arena-v2",
                public_listing=True,
            )
            result = arena(sandbox, machine, [])
            assert result["suite_version"] == "arena-v2"
            assert len(result["matches"]) == 10
            assert all(len(match["rounds"]) == 20 for match in result["matches"])
            assert result["total"] == expected[blueprint.summary]
            assert result["points_per_round"] == result["total"] / 200
            summary = entry(
                "replay",
                {
                    "kind": "arena",
                    "machine": machine.model_dump(mode="json"),
                    "result": result,
                },
            )
            assert summary is not None
            assert summary["suite_version"] == "arena-v2"
            assert summary["rounds_per_match"] == 20
            assert summary["players"][0]["strategy"] == "Rules"
            if blueprint.summary == "The Rebuilder":
                match = next(
                    m for m in result["matches"] if m["opponent"] == "The Prober"
                )
                assert match["rounds"][9]["choices"] != ["cooperate", "cooperate"]
                assert match["rounds"][10]["choices"] == ["cooperate", "cooperate"]
    finally:
        sandbox.close()


def test_legacy_players_and_direct_matches_still_use_ten_rounds() -> None:
    machine = Machine.create("Old", "Cooperate", presets()[0])
    data = machine.model_dump()
    del data["arena_version"]
    restored = Machine.model_validate(data)
    assert restored.arena_version == "arena-v1"
    sandbox = Sandbox()
    try:
        result = arena(sandbox, restored, [])
        assert result["suite_version"] == "arena-v1"
        assert result["total"] == 273
        assert len(play(sandbox, presets()[0], presets()[0])["rounds"]) == 10
    finally:
        sandbox.close()
