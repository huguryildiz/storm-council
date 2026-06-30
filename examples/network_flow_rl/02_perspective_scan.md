# Perspective Scan

## practitioner

Role and focus: The practitioner lens tests whether an RL proposal can survive NOC/SRE reality: training stability, warm-start latency, ECMP fallback, observability, rollout safety, and on-call burden. It privileges production papers, rollback designs, failure handling, and control-loop deadlines.

Priority questions: What fails at 3 a.m.? Can ECMP or shortest-path forwarding recover from a bad action? Does the controller expose enough state for incident review? How long can solve or inference latency be before the control loop misses its window? Can the system run shadow-mode before traffic exposure?

Expected evidence types: production deployment reports, incident-safe architecture descriptions, fallback mechanisms, operational playbooks, traffic replay, failure-injection tests.

Likely blind spot: It may discount advances that are technically credible but not yet productized.

Conflicts with other lenses: It will challenge the academic lens on simulation realism and the economist lens on omitted on-call cost.

Unique contribution: It will force every recommendation to include fallback and observability gates.

Escalation triggers: Any claim that a benchmark implies production readiness; any recommendation to replace a deterministic controller.

## academic

Role and focus: The academic lens evaluates DRL-for-TE literature, benchmark realism, baselines, reproducibility, and methodological scope. It privileges peer-reviewed experiments, open benchmarks, ablations, and precise support-scope limits.

Priority questions: What exactly was compared? Were hard constraints enforced by learning, optimization, or a post-processor? Are baselines strong? Are traces public? Does the paper test failures and demand shifts?

Expected evidence types: SIGCOMM/JSAC papers, arXiv preprints when full text is available, benchmark tables, ablation studies, source code releases.

Likely blind spot: It may under-weight operational rollout and accountability.

Conflicts with other lenses: It will conflict with the practitioner on deployment readiness and with the skeptic on whether benchmark gains should be trusted.

Unique contribution: It separates RL-primary results from learning-accelerated optimization.

Escalation triggers: Any claim of generalization from a single topology, trace set, or simulation setting.

## skeptic

Role and focus: The skeptic lens tests reward hacking, sim-to-real gaps, black-box audit friction, source overclaiming, and incentive problems in ML papers. It privileges negative evidence, null retrieval, scope mismatch, and missing production evidence.

Priority questions: What is not measured? Is the reward aligned with SLA outcomes? Does a cited passage entail the claim? Is the result deployment evidence or only simulation? What breaks under failures?

Expected evidence types: safety surveys, missing-source logs, contradiction records, failure-mode analyses, evidence locators.

Likely blind spot: It may reject useful hybrid ML components because RL-primary replacement is too weak.

Conflicts with other lenses: It will challenge academic performance claims, economist ROI claims, and practitioner pilot optimism.

Unique contribution: It treats absence of production evidence as a finding rather than a nuisance.

Escalation triggers: Any unsupported production-readiness claim or any recommendation that removes deterministic fallback.

## economist

Role and focus: The economist lens evaluates GPU/training cost, solver/license cost, energy, engineering time, on-call burden, opportunity cost, and risk-adjusted value. It privileges measurable cost models and reversible investments.

Priority questions: What cost does solve latency impose today? What is the marginal value of faster TE? What infrastructure and staffing does RL require? Which option is reversible? What should be measured before buying?

Expected evidence types: runtime benchmarks, solver bottleneck evidence, architecture costs, pilot metrics, staffing assumptions, opportunity-cost comparisons.

Likely blind spot: It may under-value hard-to-price safety and auditability.

Conflicts with other lenses: It will conflict with academic enthusiasm when benchmark gains lack a cost model and with practitioner caution when costs are small.

Unique contribution: It converts the decision into an option-value pilot rather than a technology preference.

Escalation triggers: Any high-cost recommendation without local runtime, labor, or incident data.

## historian

Role and focus: The historian lens compares RL-for-TE to older expert systems, MPLS TE, SDN adoption, and prior centralized-control rollouts. It privileges precedent, adoption curves, fallback patterns, and institutional memory.

Priority questions: How did previous network-control innovations enter production? What did operators preserve? Which claims sounded familiar? Did past systems replace routing or layer over it?

Expected evidence types: RFCs, production SDN papers, historical deployment reports, standards documents, architecture retrospectives.

Likely blind spot: It may assume history constrains a genuinely new method too tightly.

Conflicts with other lenses: It will challenge academic novelty claims and economist replacement narratives.

Unique contribution: It identifies hybridization as the recurring survival pattern.

Escalation triggers: Any claim that RL should skip the staged deployment path used by prior TE innovations.
