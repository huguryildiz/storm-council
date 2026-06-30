# Stage 2 prompt · Perspective Scan

> Simulate several expert perspectives, each with a position, its strongest
> evidence, and one unique insight — but as **chartered research lenses** that
> will later inspect one another, not parallel answers that get concatenated.
>
> Writes: `02_perspective_scan.md` + `02_perspective_scan.json`.

---

For the decision framed in `01_decision_frame.md` about **{{topic}}**, charter
the research lenses. Use these five by default unless I specified others —
**practitioner, academic, skeptic, economist, historian**. They are
configurable lenses, not fixed personas: each is chartered to seek a different
*kind* of evidence and to name its own blind spot.

For each lens, produce a charter:

- **Role & focus** — in two sentences, the core position the lens will pursue
  and the evidence it privileges.
- **Priority questions** — the 3–5 questions this lens must answer that the
  others would not think to ask.
- **Expected evidence types** — what counts as evidence for this lens
  (e.g. deployment post-mortems, peer-reviewed benchmarks, incentive
  disclosures, cost models, historical case studies).
- **Likely blind spot** — what this lens systematically under-weights, stated
  plainly so the system can reason about its own gaps.
- **Conflicts with other lenses** — which lenses it is most likely to disagree
  with, and on what.
- **The unique contribution** — the one thing this lens will surface that no
  other lens would tell me (this is the seed's "one thing no one else will say").
- **Escalation triggers** — the findings that should force Council Mode
  cross-examination (contested evidence, high-stakes trade-off, a requested
  recommendation).

Write the human-readable charters to `02_perspective_scan.md` and the structured
charters (one object per lens, with the fields above) to
`02_perspective_scan.json`.

Do **not** answer the research question yet — this stage only charters *how* each
lens will investigate it. If a lens is shipped as a subagent
(`storm-council:practitioner`, `…:academic`, `…:skeptic`, `…:economist`,
`…:historian`), its charter is the brief you will hand that subagent in Stage 3.
