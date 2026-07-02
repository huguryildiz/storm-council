import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RetrievalPolicyTest(unittest.TestCase):
    def test_storm_skill_requires_semantic_scholar_key_before_web_fallback(self):
        text = (ROOT / "skills" / "storm-council" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("Always try `semantic-scholar` with `SEMANTIC_SCHOLAR_API_KEY` first", text)
        self.assertIn("If no Semantic Scholar API key is configured", text)
        self.assertIn("fall back to `WebSearch` / `WebFetch`", text)

    def test_lens_agents_carry_same_retrieval_fallback_rule(self):
        expected = (
            "Always try `semantic-scholar` with `SEMANTIC_SCHOLAR_API_KEY` first; "
            "if no Semantic Scholar API key is configured, fall back to `WebSearch` / `WebFetch`."
        )
        for path in sorted((ROOT / "agents").glob("*.md")):
            if path.name == "README.md":
                continue
            with self.subTest(path=path.name):
                self.assertIn(expected, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
