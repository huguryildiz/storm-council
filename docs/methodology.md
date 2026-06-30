# Methodology

Storm Council is built on one principle:

> **Parallel answers are not the same as collective reasoning.**

Running five personas and concatenating their outputs produces breadth, not
scrutiny. Storm Council instead makes perspectives examine one another's claims,
evidence, assumptions, and uncertainties before anything is synthesised.

## 1. Research-first workflow

The decision is framed *before* research begins (Stage 1). Naming the decision,
its scope, the stakeholders, and "what would change my mind" exposes ambiguity
early and gives every later stage acceptance criteria to aim at.

## 2. Perspective diversity

Stage 2 charters several research lenses. The defaults — practitioner, academic,
skeptic, economist, historian — were chosen because they *systematically* attend
to different evidence (deployment reality, peer-reviewed results, reproducibility
and incentives, cost and opportunity cost, historical precedent). Each lens
declares its own likely blind spots, so the system reasons about its own gaps.
Lenses are configuration, not fixed roles.

## 3. Evidence / claim separation

Stage 3 records claims as structured data with an explicit `claim_type`
(fact / inference / forecast / assumption / recommendation) and `evidence_status`
(supported / partially_supported / unsupported / contested). Facts must cite a
stable source ID; unsupported claims are labelled, never silently upgraded into
conclusions. Negative evidence and *absence* of evidence are recorded explicitly.

Stage 3 also separates **publication identity** from **claim-to-source
entailment**. A paper can exist and be topically relevant without supporting a
specific claim. For direct support, Storm Council records an `evidence_id` with
an exact locator (page/section/table/figure/equation/clause/paragraph hint), a
short excerpt, a content-verification status, and the source scope
(benchmark/dataset, metric, baseline, conditions, time horizon, and deployment
vs simulation context). Abstract-only evidence cannot directly support strong
empirical, causal, comparative, quantitative, or safety-critical claims.

## 4. Contradiction-ledger logic

Stage 4 compares claims across lenses and classifies each conflict:

- **contradiction / tension** — the claims genuinely disagree;
- **scope_difference** — they are about different parts of the problem;
- **definition_conflict** — they use a key term differently;
- **evidence_gap** — the comparison that would settle it has not been done.

Each conflict carries an evidence balance, a resolution status, a next question,
and a human-review flag. Consensus is never forced; an honest "unresolved" is a
valid and valuable output.

## 5. Bounded deliberation (Council Mode)

When stakes are high or evidence is contested, the moderator runs cross-
examination. To avoid "agents talk forever", deliberation is bounded:

- a limited, *selected* set of claims is cross-examined (those in conflict,
  contested, or low-confidence first);
- each message is a single structured move — support, challenge, qualification,
  request-for-evidence, or reframing;
- there is a hard cap on rounds (default 2) and items per perspective (default
  5), and deliberation stops when no new high-impact contradiction appears.

## 6. Source-mapped synthesis

Stage 5 integrates without erasing disagreement: strongest findings, confidence-
ranked claims, evidence gaps, decision options with honest evidence strength, a
Mermaid argument map connecting question → claims → sources → tensions → actions,
and a one-page decision brief. The main disagreements are carried forward, not
hidden.

## 7. Adversarial review

Stage 6 is an independent, rule-based reviewer. It audits citation integrity,
overconfident wording, missing perspectives, source-concentration bias,
dependence on low-quality sources, contradictions hidden by the synthesis,
unjustified recommendations, missing time sensitivity, and smuggled value
judgements. It issues `PASS`, `PASS_WITH_CAVEATS`, `REVISE`, or
`BLOCKED_PENDING_EVIDENCE`, with explicit scores. Because the verdict is computed
rather than generated, the reviewer cannot be talked into approving weak work.

The deterministic verifier is intentionally limited: it checks structural and
machine-checkable preconditions (IDs, source links, DOI shape, duplicate DOI,
retracted/superseded flags, direct-support locators, abstract-only gating,
comparative-claim scope fields, and obvious overclaiming language). It does not
pretend to solve semantic entailment by itself; passage-to-claim judgement and
scope interpretation remain model/human review tasks that must be documented in
the artifacts.
