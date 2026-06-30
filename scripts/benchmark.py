#!/usr/bin/env python3
"""Run the offline Storm Council benchmark fixture suite.

The benchmark measures existing verifier behavior over labelled, pre-recorded
fixtures. It does not add verification logic, call models, or use the network.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify


EXPECTED_VERDICTS = {"PASS", "PASS_WITH_CAVEATS", "REVISE", "BLOCKED_PENDING_EVIDENCE"}
BLOCKING_VERDICTS = {"REVISE", "BLOCKED_PENDING_EVIDENCE"}
DOWNGRADE_VERDICTS = {"PASS_WITH_CAVEATS"}

SOURCE_IDENTITY_MODES = {
    "duplicate_versions",
    "preprint_superseded",
    "retracted_source",
}
OVERCLAIM_MODES = {
    "wrong_metric",
    "simulation_to_deployment",
    "association_to_causation",
    "benchmark_generalization",
    "average_to_best_overall",
    "real_paper_wrong_claim",
}


class Fixture:
    def __init__(self, path: Path, label: dict):
        self.path = path
        self.label = label


def log(message: str) -> None:
    print(message, file=sys.stderr)


def load_fixture(path: Path) -> Fixture:
    label_path = path / "label.json"
    if not label_path.exists():
        raise ValueError(f"{path} has no label.json")
    label = json.loads(label_path.read_text(encoding="utf-8"))
    expected = label.get("expected_verdict")
    failure_mode = label.get("failure_mode")
    if expected not in EXPECTED_VERDICTS:
        raise ValueError(f"{label_path} has invalid expected_verdict {expected!r}")
    if not isinstance(failure_mode, str) or not failure_mode.strip():
        raise ValueError(f"{label_path} has invalid failure_mode {failure_mode!r}")
    return Fixture(path, label)


def load_fixtures(root: Path, *, limit: int | None = None) -> list[Fixture]:
    label_paths = sorted(root.rglob("label.json"))
    fixtures = [load_fixture(p.parent) for p in label_paths]
    if limit is not None and limit < len(fixtures):
        dropped = fixtures[limit:]
        log("benchmark fixture limit dropped: " + ", ".join(_case_name(f.path, root) for f in dropped))
        fixtures = fixtures[:limit]
    return fixtures


def _case_name(path: Path, root: Path | None = None) -> str:
    if root:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            pass
    return path.as_posix()


def _all_issues(gate: dict) -> str:
    return "\n".join(
        gate.get("blocking_issues", [])
        + gate.get("major_issues", [])
        + gate.get("minor_issues", [])
    ).lower()


def _detected(failure_mode: str, gate: dict) -> dict:
    issues = _all_issues(gate)
    actual = gate["status"]
    return {
        "missing_locator": "locator" in issues,
        "source_identity_mismatch": (
            failure_mode in SOURCE_IDENTITY_MODES
            and any(term in issues for term in ("duplicate", "superseded", "retracted", "retract"))
        ),
        "overclaim_detection": (
            failure_mode in OVERCLAIM_MODES
            and any(term in issues for term in ("overclaim", "does_not_entail"))
        ),
        "abstract_only_downgrade": (
            failure_mode == "abstract_only_downgrade"
            and actual != "PASS"
            and "abstract" in issues
        ),
        "contradiction_carry_through": (
            failure_mode == "contradiction_carry_through"
            and "open contradictions remain" in issues
            and gate.get("contradiction_handling_score", 100) < 100
        ),
    }


def _metric(count: int, total: int) -> dict:
    return {
        "count": count,
        "total": total,
        "rate": round(count / total, 4) if total else None,
        "percent": round(100 * count / total, 1) if total else None,
    }


def run_benchmark(fixtures: list[Fixture], *, root: Path | None = None) -> dict:
    cases = []
    expected_counts: dict[str, int] = {}
    actual_counts: dict[str, int] = {}

    for fixture in fixtures:
        gate = verify.verify(fixture.path)
        expected = fixture.label["expected_verdict"]
        actual = gate["status"]
        failure_mode = fixture.label["failure_mode"]
        expected_counts[expected] = expected_counts.get(expected, 0) + 1
        actual_counts[actual] = actual_counts.get(actual, 0) + 1
        cases.append({
            "case": _case_name(fixture.path, root),
            "expected_verdict": expected,
            "actual_verdict": actual,
            "failure_mode": failure_mode,
            "detected": _detected(failure_mode, gate),
            "blocking_issues": gate["blocking_issues"],
            "major_issues": gate["major_issues"],
            "minor_issues": gate["minor_issues"],
            "scores": {
                "coverage": gate["coverage_score"],
                "traceability": gate["traceability_score"],
                "contradiction_handling": gate["contradiction_handling_score"],
                "recommendation_support": gate["recommendation_support_score"],
            },
        })

    false_pass_total = sum(1 for c in cases if c["expected_verdict"] != "PASS")
    false_pass_count = sum(
        1
        for c in cases
        if (
            c["expected_verdict"] in BLOCKING_VERDICTS
            and c["actual_verdict"] not in BLOCKING_VERDICTS
        )
        or (
            c["expected_verdict"] in DOWNGRADE_VERDICTS
            and c["actual_verdict"] == "PASS"
        )
    )
    false_block_total = sum(1 for c in cases if c["expected_verdict"] in {"PASS", "PASS_WITH_CAVEATS"})
    false_block_count = sum(
        1 for c in cases
        if c["expected_verdict"] in {"PASS", "PASS_WITH_CAVEATS"}
        and c["actual_verdict"] in BLOCKING_VERDICTS
    )

    def detection_metric(name: str, modes: set[str]) -> dict:
        relevant = [c for c in cases if c["failure_mode"] in modes]
        return _metric(sum(1 for c in relevant if c["detected"][name]), len(relevant))

    return {
        "totals": {
            "fixtures": len(cases),
            "expected_verdicts": dict(sorted(expected_counts.items())),
            "actual_verdicts": dict(sorted(actual_counts.items())),
        },
        "metrics": {
            "false_pass": _metric(false_pass_count, false_pass_total),
            "false_block": _metric(false_block_count, false_block_total),
            "missing_locator": detection_metric("missing_locator", {"missing_locator"}),
            "source_identity_mismatch": detection_metric("source_identity_mismatch", SOURCE_IDENTITY_MODES),
            "overclaim_detection": detection_metric("overclaim_detection", OVERCLAIM_MODES),
            "abstract_only_downgrade": detection_metric("abstract_only_downgrade", {"abstract_only_downgrade"}),
            "contradiction_carry_through": detection_metric(
                "contradiction_carry_through", {"contradiction_carry_through"}
            ),
        },
        "cases": cases,
    }


def format_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def format_text(report: dict) -> str:
    lines = [
        f"fixtures: {report['totals']['fixtures']}",
        "metrics:",
    ]
    for name, metric in report["metrics"].items():
        pct = "n/a" if metric["percent"] is None else f"{metric['percent']:.1f}%"
        lines.append(f"  {name}: {metric['count']}/{metric['total']} ({pct})")
    lines.append("cases:")
    for case in report["cases"]:
        lines.append(
            "  {case}: expected {expected_verdict}, actual {actual_verdict}, mode {failure_mode}".format(**case)
        )
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the Storm Council offline benchmark suite.")
    parser.add_argument(
        "fixture_root",
        nargs="?",
        default="tests/fixtures/benchmark",
        help="directory containing labelled benchmark fixture runs",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--limit", type=int, help="run only the first N fixtures and log dropped cases")
    args = parser.parse_args(argv)

    root = Path(args.fixture_root)
    fixtures = load_fixtures(root, limit=args.limit)
    report = run_benchmark(fixtures, root=root)
    if args.json:
        print(format_json(report), end="")
    else:
        print(format_text(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
