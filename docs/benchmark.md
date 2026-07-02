# Benchmark and evaluation

Phase 5 is a measurement layer. It runs the existing deterministic verifier over
labelled offline fixtures and records whether known failure modes are surfaced.
It does not add verification logic, call models, or use the network.

Run it with:

```bash
python3 scripts/benchmark.py
python3 scripts/benchmark.py --json
```

The suite lives in `tests/fixtures/benchmark/`. Each case is a minimal Storm
Council run directory with a `label.json`:

```json
{
  "expected_verdict": "REVISE",
  "failure_mode": "missing_locator"
}
```

`expected_verdict` is the ground-truth expected verifier outcome for the
fixture. `failure_mode` is unique across the suite so metric coverage is
auditable.

## Current results

Measured on 2026-07-02 with `python3 scripts/benchmark.py`:

| Metric | Result | Meaning |
| --- | ---: | --- |
| False pass | 0/15 (0.0%) | A fixture expected to block or downgrade did not pass cleanly. |
| False block | 0/5 (0.0%) | A fixture expected to downgrade was not escalated to a hard block. |
| Missing locator | 1/1 (100.0%) | Direct support without a concrete evidence locator was caught. |
| Source identity mismatch | 3/3 (100.0%) | Duplicate, superseded, or retracted source identity cases were surfaced. |
| Overclaim detection | 8/8 (100.0%) | Scope, metric, benchmark, deployment, and causal overclaims were surfaced. |
| Abstract-only downgrade | 2/2 (100.0%) | Abstract-only support for a strong direct claim was blocked/downgraded. |
| Passage entailment clean | 1/1 (100.0%) | A valid local support packet with `entails/yes` counted as passage-checked. |
| Passage quote integrity | 1/1 (100.0%) | A support packet whose quote is absent from local source material was caught. |
| Metadata-only not passage-checked | 1/1 (100.0%) | DOI metadata without a support packet stayed `not_checked`. |
| Contradiction carry-through | 1/1 (100.0%) | An unresolved contradiction stayed visible in the verifier output. |

## Covered cases

| Fixture | Expected verdict | Failure mode |
| --- | --- | --- |
| `wrong-paper/wrong-claim` | `REVISE` | `real_paper_wrong_claim` |
| `correct-topic/wrong-metric` | `REVISE` | `wrong_metric` |
| `simulation-to-deployment` | `REVISE` | `simulation_to_deployment` |
| `association-to-causation` | `REVISE` | `association_to_causation` |
| `benchmark-generalization` | `REVISE` | `benchmark_generalization` |
| `abstract-only-downgrade` | `REVISE` | `abstract_only_downgrade` |
| `preprint-superseded` | `PASS_WITH_CAVEATS` | `preprint_superseded` |
| `retracted-source` | `REVISE` | `retracted_source` |
| `duplicate-versions` | `PASS_WITH_CAVEATS` | `duplicate_versions` |
| `average-to-best-overall` | `REVISE` | `average_to_best_overall` |
| `missing-locator` | `REVISE` | `missing_locator` |
| `contradiction-carry-through` | `PASS_WITH_CAVEATS` | `contradiction_carry_through` |
| `metadata-only-real-doi` | `PASS` | `metadata_only_real_doi` |
| `clean-passage-entails` | `PASS` | `clean_passage_entails` |
| `quote-not-in-source` | `REVISE` | `quote_not_in_source` |
| `abstract-only-overclaim` | `REVISE` | `abstract_only_overclaim` |
| `real-paper-wrong-claim` | `REVISE` | `real_paper_wrong_claim_packet` |

## Adding a fixture

1. Add a minimal run directory under `tests/fixtures/benchmark/<case>/`.
2. Include only pre-recorded artifacts: claims, source registry, evidence,
   verdicts, support packets/source material, contradictions, and metadata files
   as needed.
3. Add `label.json` with `expected_verdict` and a unique `failure_mode`.
4. Run `python3 scripts/benchmark.py` and update the current results table if
   the measured metric totals change.
5. Run `python3 -m unittest discover -s tests`.

If a future bounded run adds sampling or top-N selection, it must log every
dropped fixture. The current CLI `--limit` option does this explicitly on
stderr.
