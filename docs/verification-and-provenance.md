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
