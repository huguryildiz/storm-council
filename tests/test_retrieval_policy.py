import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AGENT_RULE = (
    "Always try `semantic-scholar` with `SEMANTIC_SCHOLAR_API_KEY` first; "
    "if no Semantic Scholar API key is configured, fall back to `OpenAlex` "
    "(via `paper-search` `search_openalex`, with `OPENALEX_API_KEY`); if OpenAlex "
    "is also unavailable, fall back to `WebSearch` / `WebFetch`. When both Semantic "
    "Scholar and OpenAlex return the same paper, double-check them against each other "
    "(DOI, title, year) and record any divergence in `metadata_mismatches`."
)


class RetrievalPolicyTest(unittest.TestCase):
    def test_storm_skill_enforces_three_tier_ladder(self):
        import re
        raw = (ROOT / "skills" / "storm-council" / "SKILL.md").read_text(encoding="utf-8")
        text = re.sub(r"\s+", " ", raw)  # collapse line-wrapping so substrings match

        # Tier 1 -> Semantic Scholar first.
        self.assertIn("Always try `semantic-scholar` with `SEMANTIC_SCHOLAR_API_KEY` first", text)
        # Tier 2 -> OpenAlex second.
        self.assertIn("If no Semantic Scholar API key is configured", text)
        self.assertIn("fall back to **OpenAlex**", text)
        # Tier 3 -> web search last.
        self.assertIn("fall back to `WebSearch` / `WebFetch`", text)
        self.assertIn("web search is a last resort, not a shortcut past OpenAlex", text)
        # Double-check rule.
        self.assertIn("Double-check (hard rule).", text)
        self.assertIn("metadata_mismatches", text)

    def test_lens_agents_carry_same_retrieval_ladder_and_double_check(self):
        for path in sorted((ROOT / "agents").glob("*.md")):
            if path.name == "README.md":
                continue
            with self.subTest(path=path.name):
                self.assertIn(AGENT_RULE, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
