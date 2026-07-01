# Limitations

Storm Council is decision support. It can make evidence, disagreement, and
verification status easier to inspect, but it cannot remove the need for human
judgement.

## Model Output Risk

The model can hallucinate, overgeneralize, or choose weak evidence. The workflow
requires source IDs and evidence locators, and the verifier checks structure and
selected guardrails, but those checks do not guarantee truth.

## Retrieval Risk

Retrieval tools may be absent, unavailable, biased, stale, or incomplete. If no
retrieval tool actually returned a source, the run must not claim retrieval or
source verification happened.

## Citation Quality

A real source can be irrelevant to the specific claim. A title, abstract, or
similar topic is not enough for direct support of strong empirical, causal,
comparative, quantitative, or safety-critical claims.

## Prompt Sensitivity

The workflow is implemented as prompt/runbook instructions plus deterministic
post-processing. Different user framing, source availability, or model behavior
can change the artifacts.

## Local Integrity vs External Trust

`--seal` and `--check-seal` are local integrity checks. They do not create a
trusted timestamp, signature, authorship proof, or legal chain of custody.

## Consequential Decisions

For legal, medical, financial, policy, safety, security, or major operational
decisions, the output supports review by qualified people. It is not professional
advice and should not trigger automated action without accountable human review.
