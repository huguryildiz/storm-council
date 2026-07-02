"""Golden-file guardrail for the render_report refactor (roadmap Phase 6).

Reproduces the exact pipeline that produced each example's committed
``storm_council_report.html`` (enrich -> fold(all) -> build(all)) and asserts the
output is byte-identical. This is the refactor guardrail: any behavior change in
the renderer package shows up here as a non-empty diff.
"""
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_report", ROOT / "scripts" / "render_report.py"
)
render_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_report)

EXAMPLES = ("network_flow_rl", "ai_jobs_policy")
_SEALED_AT_RE = re.compile(
    r'(<tr><th scope="row">Sealed</th><td><time class="ts-local" data-ts=")'
    r'[^"]+'
    r'(">)[^<]+(</time></td></tr>)'
)
_SELF_HASH_RE = re.compile(
    r'<li><span class="sid">storm_council_report\.html</span> <code>'
    r'[0-9a-f]{64}</code> <span class="ty">[^<]+</span></li>'
)


class RenderGoldenTest(unittest.TestCase):
    def _rendered(self, example: str) -> str:
        base = ROOT / "examples" / example
        data = json.loads((base / "report_data.json").read_text(encoding="utf-8"))
        render_report._enrich_source_urls(data, base)
        render_report._fold_in_artifacts(data, base, "all")
        return render_report.build(data, "all")

    def _normalize_seal_time(self, html: str) -> str:
        html = _SEALED_AT_RE.sub(r"\1<sealed-at>\2<sealed-at>\3", html)
        return _SELF_HASH_RE.sub(
            '<li><span class="sid">storm_council_report.html</span> '
            '<code><report-html-sha256></code> '
            '<span class="ty">· <report-html-bytes> bytes</span></li>',
            html,
        )

    def test_examples_render_byte_identical_to_committed_html(self):
        for example in EXAMPLES:
            with self.subTest(example=example):
                base = ROOT / "examples" / example
                want = (base / "storm_council_report.html").read_text(encoding="utf-8")
                self.assertEqual(
                    self._normalize_seal_time(self._rendered(example)),
                    self._normalize_seal_time(want),
                )


if __name__ == "__main__":
    unittest.main()
