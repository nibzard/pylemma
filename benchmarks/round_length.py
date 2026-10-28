"""Offline experiment; the production round count remains unchanged.

Run inside the deployed image with --network none --cpus .25.
Use the actual match function with only its two round-count constants replaced
in memory. No generated players, provider requests, or hosted writes are used.
"""

import inspect
import json
import statistics
import sys
import time
from contextlib import nullcontext

from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import pylemma.machines as machines
from pylemma.telemetry import configure, match_context


def blueprint(name, body):
    return machines.Blueprint(
        summary=name,
        code="def decide(observation):\n"
        "    h = observation['history']\n"
        "    n = observation['round']\n"
        + "\n".join("    " + line for line in body.splitlines())
        + "\n    return {'choice': c, 'stated_reason': 'Offline experiment.'}\n",
    )


strategies = {
    "cooperate": "c = 'cooperate'",
    "betray": "c = 'betray'",
    "copy": "c = h[-1]['opponent'] if h else 'cooperate'",
    "forgive": (
        "c = 'betray' if len(h) >= 2 and "
        "all(r['opponent'] == 'betray' for r in h[-2:]) else 'cooperate'"
    ),
    "grim": (
        "c = 'betray' if any(r['opponent'] == 'betray' for r in h) else 'cooperate'"
    ),
    "pavlov": """c = 'cooperate'
if h:
    last = h[-1]
    if last['opponent'] == 'cooperate':
        c = last['self']
    else:
        c = 'betray' if last['self'] == 'cooperate' else 'cooperate'""",
    "alternate": "c = 'cooperate' if n % 2 else 'betray'",
    "probe": (
        "c = 'betray' if n % 7 == 0 else (h[-1]['opponent'] if h else 'cooperate')"
    ),
    "suspicious_copy": "c = h[-1]['opponent'] if h else 'betray'",
    "rebuild": """remaining = 0
peace = 0
for r in h:
    if remaining:
        remaining -= 1
        if remaining == 0:
            peace = 2
    elif peace:
        peace -= 1
    elif r['opponent'] == 'betray':
        remaining = 2
c = 'betray' if remaining else 'cooperate'""",
}
players = {name: blueprint(name, body) for name, body in strategies.items()}
source = inspect.getsource(machines.play)
assert source.count("range(1, 11)") == 1
assert source.count('"rounds": 10') == 1


def match_function(rounds):
    namespace = vars(machines).copy()
    exec(
        source.replace("range(1, 11)", f"range(1, {rounds + 1})").replace(
            '"rounds": 10', f'"rounds": {rounds}'
        ),
        namespace,
    )
    return namespace["play"]


tracing = "--telemetry" in sys.argv
exporter = InMemorySpanExporter()
telemetry = (
    configure(send_to_logfire=False, processors=[SimpleSpanProcessor(exporter)])
    if tracing
    else None
)
context = match_context(telemetry) if tracing else nullcontext()
sandbox = machines.Sandbox()
output = {
    "cpu_limit": 0.25,
    "repeats": 3,
    "telemetry": "local memory exporter" if tracing else "disabled",
    "results": [],
}
try:
    functions = {n: match_function(n) for n in (10, 20)}
    actual = machines.play(sandbox, players["copy"], players["probe"])
    experimental = functions[10](sandbox, players["copy"], players["probe"])
    assert actual == experimental
    context.__enter__()
    for candidate in ("copy", "forgive", "rebuild"):
        samples = {10: [], 20: []}
        outcomes = {}
        trace_sizes = {}
        for repeat in range(3):
            for length in (10, 20) if repeat % 2 == 0 else (20, 10):
                exporter.clear()
                start = time.perf_counter()
                results = {
                    name: functions[length](sandbox, players[candidate], opponent)
                    for name, opponent in players.items()
                }
                samples[length].append(time.perf_counter() - start)
                spans = exporter.get_finished_spans()
                trace_sizes[length] = {
                    "spans": len(spans),
                    "attribute_json_bytes": sum(
                        len(json.dumps(dict(span.attributes or {})).encode())
                        for span in spans
                    ),
                }
                for result in results.values():
                    result["trace_id"] = None
                    for turn in result["rounds"]:
                        turn["span_id"] = None
                assert all(
                    len(result["rounds"]) == length for result in results.values()
                )
                if length in outcomes:
                    assert results == outcomes[length]
                outcomes[length] = results
        row = {"candidate": candidate, "lengths": {}, "opponents": []}
        for length in (10, 20):
            results = outcomes[length]
            row["lengths"][length] = {
                "seconds": samples[length],
                "trace": trace_sizes[length],
                "median_seconds": statistics.median(samples[length]),
                "points_per_round": sum(r["totals"][0] for r in results.values())
                / (length * len(players)),
                "cooperation_rate": sum(r["cooperation"][0] for r in results.values())
                / (length * len(players)),
                "mutual_cooperation_rate": sum(
                    turn["choices"] == ["cooperate", "cooperate"]
                    for r in results.values()
                    for turn in r["rounds"]
                )
                / (length * len(players)),
            }
        for name in players:
            short, long = outcomes[10][name], outcomes[20][name]
            assert short["rounds"] == long["rounds"][:10]
            row["opponents"].append(
                {
                    "name": name,
                    "points_per_round_10": short["totals"][0] / 10,
                    "points_per_round_20": long["totals"][0] / 20,
                    "choices": [
                        "".join("C" if c == "cooperate" else "D" for c in r["choices"])
                        for r in long["rounds"]
                    ],
                    "late_recoveries": [
                        r["round"]
                        for previous, r in zip(
                            long["rounds"], long["rounds"][1:], strict=False
                        )
                        if r["round"] > 10
                        and previous["choices"] != ["cooperate", "cooperate"]
                        and r["choices"] == ["cooperate", "cooperate"]
                    ],
                }
            )
        output["results"].append(row)
finally:
    context.__exit__(None, None, None)
    sandbox.close()
print(json.dumps(output, indent=2))
