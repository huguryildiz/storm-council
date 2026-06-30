import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("benchmark", ROOT / "scripts" / "benchmark.py")
benchmark_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark_mod)


class BenchmarkFixtureTest(unittest.TestCase):
    def test_benchmark_suite_has_twelve_distinct_labelled_cases(self):
        fixtures = benchmark_mod.load_fixtures(ROOT / "tests" / "fixtures" / "benchmark")

        self.assertEqual(len(fixtures), 12)
        self.assertEqual(len({f.label["failure_mode"] for f in fixtures}), 12)
        for fixture in fixtures:
            self.assertIn("expected_verdict", fixture.label)
            self.assertIn("failure_mode", fixture.label)

    def test_metrics_match_hand_computed_subsuite(self):
        suite = ROOT / "tests" / "fixtures" / "benchmark"
        fixtures = [
            benchmark_mod.load_fixture(suite / "duplicate-versions"),
            benchmark_mod.load_fixture(suite / "missing-locator"),
            benchmark_mod.load_fixture(suite / "wrong-paper" / "wrong-claim"),
        ]

        report = benchmark_mod.run_benchmark(fixtures)

        self.assertEqual(report["totals"]["fixtures"], 3)
        self.assertEqual(report["metrics"]["false_pass"]["count"], 0)
        self.assertEqual(report["metrics"]["false_pass"]["total"], 3)
        self.assertEqual(report["metrics"]["false_block"]["count"], 0)
        self.assertEqual(report["metrics"]["false_block"]["total"], 1)
        self.assertEqual(report["metrics"]["missing_locator"]["count"], 1)
        self.assertEqual(report["metrics"]["missing_locator"]["total"], 1)

    def test_full_suite_expected_metrics_are_locked(self):
        report = benchmark_mod.run_benchmark(
            benchmark_mod.load_fixtures(ROOT / "tests" / "fixtures" / "benchmark")
        )

        expected = {
            "false_pass": (0, 12),
            "false_block": (0, 3),
            "missing_locator": (1, 1),
            "source_identity_mismatch": (3, 3),
            "overclaim_detection": (6, 6),
            "abstract_only_downgrade": (1, 1),
            "contradiction_carry_through": (1, 1),
        }
        for metric, (count, total) in expected.items():
            with self.subTest(metric=metric):
                self.assertEqual(report["metrics"][metric]["count"], count)
                self.assertEqual(report["metrics"][metric]["total"], total)

    def test_mislabelled_blocking_fixture_fails_regression_guard(self):
        suite = ROOT / "tests" / "fixtures" / "benchmark"
        fixtures = benchmark_mod.load_fixtures(suite)
        mutated = []
        for fixture in fixtures:
            if fixture.path.name == "missing-locator":
                label = dict(fixture.label)
                label["expected_verdict"] = "PASS"
                mutated.append(benchmark_mod.Fixture(fixture.path, label))
            else:
                mutated.append(fixture)

        report = benchmark_mod.run_benchmark(mutated)

        self.assertGreater(report["metrics"]["false_block"]["count"], 0)

    def test_cli_json_output_is_parseable(self):
        report = benchmark_mod.run_benchmark(
            benchmark_mod.load_fixtures(ROOT / "tests" / "fixtures" / "benchmark")
        )

        encoded = benchmark_mod.format_json(report)

        self.assertEqual(json.loads(encoded)["totals"]["fixtures"], 12)


if __name__ == "__main__":
    unittest.main()
