"""Golden-file guardrail for the render_report refactor (roadmap Phase 6).

Reproduces the exact pipeline that produced each example's committed
``storm_council_report.html`` (enrich -> fold(all) -> build(all)) and asserts the
output is byte-identical. This is the refactor guardrail: any behavior change in
the renderer package shows up here as a non-empty diff.
"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_report", ROOT / "scripts" / "render_report.py"
)
render_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_report)

EXAMPLES = ("network_flow_rl", "ai_jobs_policy")


class RenderGoldenTest(unittest.TestCase):
    def _rendered(self, example: str) -> str:
        base = ROOT / "examples" / example
        data = json.loads((base / "report_data.json").read_text(encoding="utf-8"))
        render_report._enrich_source_urls(data, base)
        render_report._fold_in_artifacts(data, base, "all")
        return render_report.build(data, "all")

    def test_examples_render_byte_identical_to_committed_html(self):
        for example in EXAMPLES:
            with self.subTest(example=example):
                base = ROOT / "examples" / example
                want = (base / "storm_council_report.html").read_text(encoding="utf-8")
                self.assertEqual(self._rendered(example), want)


if __name__ == "__main__":
    unittest.main()
