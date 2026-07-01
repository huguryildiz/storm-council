"""Phase 5 repo lint: the three template lens agents must genuinely differ.

Before Phase 5 the economist / historian / practitioner prompts shared a nearly
identical body (>80 % overlap), so "five lenses" was largely cosmetic. This test
pins the differentiation in place: every pair of the three files must be less than
80 % identical. It is a static text lint — no rendering, no network.
"""

import difflib
import itertools
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LENS_FILES = ["economist.md", "historian.md", "practitioner.md"]
MAX_SIMILARITY = 0.80


class LensFilesDivergeTest(unittest.TestCase):
    def _text(self, name):
        return (ROOT / "agents" / name).read_text(encoding="utf-8")

    def test_three_template_lenses_are_not_over_80_percent_identical(self):
        for a, b in itertools.combinations(LENS_FILES, 2):
            ratio = difflib.SequenceMatcher(None, self._text(a), self._text(b)).ratio()
            self.assertLess(
                ratio, MAX_SIMILARITY,
                f"{a} and {b} are {ratio:.0%} identical (must be < {MAX_SIMILARITY:.0%}); "
                "give each lens a distinct method + retrieval steering.")

    def test_each_lens_has_its_own_retrieval_steering(self):
        # Differentiation must include per-lens retrieval steering, not just a
        # renamed focus line.
        for name in LENS_FILES:
            self.assertIn("## How to retrieve evidence", self._text(name), name)


if __name__ == "__main__":
    unittest.main()
