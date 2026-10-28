# Compare ten and twenty rounds

## Objective

Check whether twenty rounds reveal useful behavior without a large runtime increase.

## Relevant specification sections

Execution and scoring, simple arena, and section 16.1 apply.
This is an isolated experiment. The deployed ten-round contract remains unchanged.

## Files and contracts changed

Add an offline benchmark using the actual match implementation with two constants replaced in memory.
No application contracts change.

## Decisions and reasons

Compare three candidates against the same ten deterministic opponents.
Use three repetitions and alternate execution order.
Run the deployed Docker image with its 0.25 CPU allocation and network disabled.
Normalize scores by round count.
Assert equal results across repetitions and identical first ten rounds.
Check the experimental ten-round function against the unchanged production function.

## Simplicity review

A standalone experiment avoids adding a new game mode before evidence exists.
No dependencies or production abstractions are needed.
An optional local trace exporter measures trace creation without sending data.

## Checks run and results

Ran the benchmark in the deployed image with network disabled and 0.25 CPU.
Each mode ran 180 matches: three candidates, ten opponents, two lengths, and three repetitions.
Each mode evaluated 5,400 decisions, plus two ten-round equivalence checks.
All round-count, repeated-result, and first-ten-round assertions passed.
A local memory exporter verified that enabling traces did not change choices or scores.
No credentials, generation quota, or hosted records were used.

Commands:
- docker run --rm --network none --cpus .25 -v "$PWD/benchmarks/round_length.py:/round_length.py:ro" pylemma:deploy python3 /round_length.py
- Repeat with --telemetry to enable a local trace exporter.
- Ruff lint and format checks for the benchmark: passed.
- git diff --check: passed.
- Tracked and unignored file fingerprints matched before and after checks.
- A final untraced run matched every traced choice and score after formatting corrections.

The image is based on digest 1b24ccda7d43540a91bef56685ed63ca219b595281e0f05733290ab0e00642d0.

| Candidate | 10 rounds, median seconds | 20 rounds, median seconds | Points per round, 10 | Points per round, 20 |
| --- | ---: | ---: | ---: | ---: |
| Copy the last move | 0.413 | 0.906 | 2.650 | 2.585 |
| Retaliate after two consecutive betrayals | 0.408 | 0.915 | 2.570 | 2.595 |
| Punish twice, then cooperate twice | 0.485 | 0.991 | 2.530 | 2.545 |

Times include local trace creation and export to memory, but exclude network export and hosted request overhead.
Without trace creation, ten-round arenas had medians of 0.103–0.107 seconds.
Twenty-round arenas had medians of 0.207–0.286 seconds.

Ten-round arenas produced 310 completed spans and 255,693–258,600 bytes of serialized span attributes.
Twenty-round arenas produced 610 completed spans and 601,927–606,246 bytes.
Attribute bytes grew about 2.35 times. These bytes are not Logfire billing units or compressed wire sizes.

The ten opponents are cooperate, betray, copy, forgive, grim, Pavlov, alternate, periodic probe, suspicious copy, and rebuild.
The periodic probe betrays every seventh round and otherwise copies the previous move.
The rebuild strategy punishes for two rounds, then cooperates for two rounds.
It ignores fresh betrayals during those punishment and recovery phases.

Against the periodic probe, rebuild produced:
- Rounds 1–6: mutual cooperation.
- Round 7: the probe betrayed.
- Rounds 8–10: retaliation and attempted recovery.
- Round 11: mutual cooperation resumed.
- Round 18: mutual cooperation resumed after another probe.

A ten-round replay ends before the first successful recovery.
Against most other opponents, extra rounds extend behavior already visible in the first ten.
The small score difference between copy and forgive reversed at twenty rounds.
This is evidence that duration affects comparisons, not evidence of a universal winning strategy.

## Failures and verified corrections

Initial lint checks found long lines, import ordering, and an unspecified zip length policy.
Formatting and explicit strict=False corrected those issues.

## Known limits

Synthetic opponents do not represent the changing public leaderboard.
The first run excludes telemetry. The second includes trace creation and local export.
Both exclude HTTP, remote storage, network export, and cold startup.
The experiment measures execution and behavior, not whether people find longer games more enjoyable.
Strategies in this suite do not change behavior based on the announced match length.

## Next implementation step

The experiment supports trying twenty rounds: the measured execution increase is about half a second per arena.
It does not establish hosted end-to-end latency or user enjoyment.
Keep production at ten rounds until a coordinated rules change updates generation, scoring displays, and replay versioning.
Do not reinterpret stored players that explicitly mention round ten.
