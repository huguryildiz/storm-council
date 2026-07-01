# Recheck and Refresh

Recheck is a manual, point-in-time publication-identity refresh for a finished
bundle. It is not continuous monitoring.

## Command

```bash
python3 scripts/verify.py <output_dir> --recheck --write
python3 scripts/verify.py <output_dir> --recheck --offline
```

`--recheck` re-runs the same publication-identity adapter seam used by
`metadata_adapters.py`, compares before/after source states, re-runs
`verify.py`, and writes a deterministic diff when `--write` is present.

## Outputs

| File | Meaning |
| --- | --- |
| `refresh_diff.json` | Machine-readable before/after source, claim, contradiction, tripwire, and gate diff |
| `refresh_report.md` | Human-readable recheck summary |
| `06_quality_gate.json` | Updated after-gate under `--write` |
| `provenance_manifest.json` | Rewritten after `--recheck --write` so the refreshed bundle can pass `--check-seal` |

## Change Classes

Source changes use a closed set:

- `unchanged`;
- `retracted`;
- `superseded`;
- `corrected`;
- `unavailable`;
- `not_rechecked`.

`not_rechecked` is an honest uncertainty state. It is chosen before comparing
flags when no resolvable identifier is available, adapters are offline, or cache
only mode has no usable response. It must not be described as unchanged.

## What Can Change

Recheck can change the computed gate and can surface weakened claims when a
source becomes retracted, superseded, corrected, unavailable, or not rechecked.
It does not rewrite claim text, evidence status, contradiction status, or
recommendations. A human or a fresh Storm Council run must decide whether to
update the analysis.

## Tripwires

Optional `decision_tripwires.json` entries can mark a condition as
`auto_recheckable` only when it binds to a resolvable source or DOI metadata
event. Otherwise it is a `manual_watch` condition for human review.
