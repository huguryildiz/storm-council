# NOTICE

## Attribution

Storm Council is **inspired by** research-first knowledge-curation systems such
as [Stanford OVAL's **STORM** (*Synthesis of Topic Outlines through Retrieval
and Multi-perspective Question Asking*)](https://github.com/stanford-oval/storm).
The conceptual debt is to the broader idea of multi-perspective inquiry grounded
in retrieval and bounded deliberation.

## Non-affiliation

Storm Council is **independently developed** and is **not affiliated with,
endorsed by, or derived from**:

- Stanford University or Stanford OVAL,
- the STORM project,
- Anthropic or Claude Code,
- YouMind,

or any other organisation. The name "Storm Council" is an **homage** to that
research lineage, not a claim of affiliation, endorsement, or shared provenance.

No text, prompts, diagrams, headings, code, or examples were copied from those
sources. The workflow, prompt templates, role charters, schemas, examples, and
documentation in this repository were written independently.

## Bundled agent files

The five research lens subagents in `agents/` (`academic`, `economist`,
`historian`, `practitioner`, `skeptic`) are original works written for this
project. They reference no third-party content and carry no separate license
beyond the Apache 2.0 license that covers this repository.

## Synthetic data notice

The bundled university-timetabling example is produced by a **deterministic mock
adapter**, not by live retrieval. It cites real, well-known works for realism and
**one explicitly synthetic source (`S-010`)** used to exercise the review stage.
Every artifact carries a banner saying so. Treat all example sources as
illustrative and verify them independently before relying on anything.

## Dependencies

The `scripts/verify.py` and `scripts/render_report.py` scripts use the Python
standard library only — no third-party packages, no network requests, no LLM
calls, no API key.

## License

Storm Council is licensed under the Apache License, Version 2.0. See
[`LICENSE`](LICENSE).
