# Verification and Provenance

Storm Council separates artifact integrity from factual truth.

## What `verify.py` Proves

`scripts/verify.py` checks deterministic conditions in saved artifacts:

- claim/source/evidence/contradiction IDs resolve;
- supported facts and inferences cite registered sources;
- direct-support claims have concrete evidence locators;
- passage support packets stay under `source_material/`, hash the local text
  file, and quote text that is present in that file;
- required evidence verdicts exist and use valid enum values;
- `does_not_entail` and `overclaimed` verdicts block direct/strong/comparative support;
- DOI normalization, duplicate source versions, retractions, corrections, and
  supersessions are surfaced when encoded in source metadata;
- abstract-only sources cannot directly support strong claims;
- comparative claims include scope fields such as metric, baseline, and dataset;
- obvious overclaiming language is surfaced for review;
- recommendations and next actions point back to evidence or conflict IDs.

It computes `coverage_score`, `traceability_score`,
`argument_support_score`, `contradiction_handling_score`,
`recommendation_support_score`, `argument_support_status`, and a status:
`PASS`, `PASS_WITH_CAVEATS`, `REVISE`, or `BLOCKED_PENDING_EVIDENCE`.

## What It Does Not Prove

`verify.py` does not prove that:

- a model found every relevant source;
- a cited passage semantically entails a claim;
- a DOI-resolved source supports the cited claim unless a support packet and
  verdict exist for that claim/evidence pair;
- a recommendation is true or sufficient;
- a source remains current unless rechecked;
- a seal was created by a trusted person.

## Commands

```bash
python3 scripts/verify.py <output_dir> --write
python3 scripts/verify.py <output_dir> --strict
```

`--write` writes `06_quality_gate.json` and patches `report_data.json`.
`--strict` exits with status 2 when the computed verdict is `REVISE` or
`BLOCKED_PENDING_EVIDENCE`.

## Publication Identity

```bash
python3 scripts/metadata_adapters.py <output_dir>
python3 scripts/metadata_adapters.py <output_dir> --no-retrieve
```

The adapter script writes `metadata_verification.jsonl`,
`source_versions.jsonl`, and `retrieval_log.jsonl`. It checks publication
identity and version/retraction state where adapters can resolve a source. It
does not check whether the source supports a specific claim.

## Provenance Seal

```bash
python3 scripts/verify.py <output_dir> --seal
python3 scripts/verify.py <output_dir> --check-seal
```

`--seal` requires an existing `06_quality_gate.json`. It writes
`provenance_manifest.json` with SHA-256 hashes for artifacts in the directory and
copies the verdict at seal time. `--check-seal` re-hashes and reports `PASS` or
`ALTERED`.

This is integrity, not authenticity. A matching unsigned manifest means the
bundle is byte-identical to the last seal. It does not prove who sealed it, and
someone with write access can alter files and regenerate the manifest.

## Tampering Behavior

If a sealed file changes, `--check-seal` reports `ALTERED` and lists altered,
missing, or added files. If the manifest itself is rewritten to match the altered
bundle, the unsigned manifest cannot detect that rewrite.

## Recheck and Refresh

Recheck is a manual, point-in-time publication-identity refresh for a finished
bundle. It is not continuous monitoring.

```bash
python3 scripts/verify.py <output_dir> --recheck --write
python3 scripts/verify.py <output_dir> --recheck --offline
```

`--recheck` re-runs the same publication-identity adapter seam used by
`metadata_adapters.py`, compares before/after source states, re-runs
`verify.py`, and writes a deterministic diff when `--write` is present.

| File | Meaning |
| --- | --- |
| `refresh_diff.json` | Machine-readable before/after source, claim, contradiction, tripwire, and gate diff |
| `refresh_report.md` | Human-readable recheck summary |
| `06_quality_gate.json` | Updated after-gate under `--write` |
| `provenance_manifest.json` | Rewritten after `--recheck --write` so the refreshed bundle can pass `--check-seal` |

Source changes use a closed set: `unchanged`, `retracted`, `superseded`,
`corrected`, `unavailable`, `not_rechecked`. `not_rechecked` is an honest
uncertainty state, chosen before comparing flags when no resolvable identifier
is available, adapters are offline, or cache-only mode has no usable response.
It must not be described as unchanged.

Recheck can change the computed gate and can surface weakened claims when a
source becomes retracted, superseded, corrected, unavailable, or not rechecked.
It does not rewrite claim text, evidence status, contradiction status, or
recommendations. A human or a fresh Storm Council run must decide whether to
update the analysis.

Optional `decision_tripwires.json` entries can mark a condition as
`auto_recheckable` only when it binds to a resolvable source or DOI metadata
event. Otherwise it is a `manual_watch` condition for human review.
