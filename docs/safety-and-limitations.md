# Safety and limitations

Storm Council is decision-*support*. It is designed to make uncertainty and
disagreement visible — not to remove the human from the decision.

## Model hallucination risk

A real LLM adapter can fabricate claims or sources. Storm Council mitigates this
by requiring source IDs and by running an independent citation-integrity check,
but it cannot guarantee a model did not invent a plausible-looking source.
**Verify sources before relying on them.**

## Retrieval quality risk

If a retrieval adapter returns weak, outdated, or biased material, the
downstream claims inherit those flaws. The reviewer flags low-credibility
sources and source concentration, but garbage in still degrades the output.

## Source bias

Over-reliance on a single publisher, venue, or viewpoint skews conclusions. The
review stage reports the dominant source type and flags supported claims that
lean on low-credibility sources.

## False consensus

The biggest failure mode of multi-agent tools is manufacturing agreement. Storm
Council treats disagreement as a first-class artifact and explicitly checks for
"unresolved contradictions hidden by the synthesis." An honest `unresolved` is
preferred to a fake consensus.

## Over-automation risk

Scores are heuristic decision-support, not ground truth. A `PASS` means the
artifacts cleared the integrity checks — not that the recommendation is correct.
Do not wire the quality gate to an automated action without human review.

## Domain-expert review

For anything consequential, a domain expert must review the claims, sources, and
contradictions. The brief is a starting point for that review, not a substitute.

## Sensitive / high-stakes uses

Storm Council is **not** professional, legal, medical, financial, or policy
advice. Topics in those areas auto-escalate to Council Mode and should carry
explicit caveats; they still require qualified human judgement.

## Personal data

Do not put personal or confidential data into topics, claims, or sources. The
artifacts are plain files and may be shared; treat them accordingly.
