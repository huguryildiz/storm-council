# Stage 1 prompt · Decision Frame

> Rigorous research begins by framing the decision so every later stage has
> something to aim at — one step before any perspective is gathered.
>
> Writes: `01_decision_frame.md` (shape: [`../templates/decision_frame.md`](../templates/decision_frame.md)).
> May also write: `decision_tripwires.json` (shape: [`../templates/decision_tripwires.json`](../templates/decision_tripwires.json)).

---

I need to research **{{topic}}**.

Before producing any perspectives or evidence, frame the decision. Ask me only
the framing questions you genuinely cannot infer from the request — at most a
few, short. If I have already supplied an answer, do not re-ask it.

1. **Decision & audience.** What decision will this research inform, and who
   acts on it? State it as a single decision question.
2. **Scope & exclusions.** What is explicitly in scope, and what is out of
   scope for this run?
3. **Time horizon & risk tolerance.** Over what period must the answer hold,
   and how costly is being wrong?
4. **Stakeholders.** Who is affected by the decision or the evidence?
5. **What would change the answer.** Name the findings that would flip the
   recommendation — this becomes the research's acceptance criteria. Also emit
   draft `decision_tripwires.json` entries for these conditions when enough
   claim/option context exists. Prioritize `decision_criticality.json`'s
   `most_load_bearing` / pivotal claims if that artifact is already present;
   otherwise keep the entries unranked. Each tripwire must use `T-###`, bind to
   at least one real `C-###` claim or an exact `report_data.json` option name,
   state `direction` as `strengthens`, `weakens`, or `invalidates`, and keep
   `reversal_cost` to `low`, `medium`, or `high`. Use `manual_watch` unless the
   monitoring source is a real `S-###` or DOI that metadata adapters can later
   re-check for retraction/supersession. Do not invent numeric thresholds,
   probabilities, percentages, schedules, polling, or alerts.
6. **Known uncertainties.** What is already known to be unknown going in?

Then write `01_decision_frame.md` covering: the decision question, why it
matters, scope, exclusions, key assumptions, stakeholders, what would change the
decision, known uncertainties, and research acceptance criteria.

If you write `decision_tripwires.json`, make it a flat array of `T-###` records,
not a nested field in `report_data.json`. `manual_watch` means a human must
check the condition; never describe it as tracked, monitored, or watched by the
system. `auto_recheckable` is only for source-metadata events a later
`metadata_adapters`/`--recheck` pass can resolve from a real source ID or DOI.

Acceptance criteria must include, at minimum:
- every factual claim ties to a stable source ID;
- the major cross-perspective contradictions are surfaced explicitly;
- the brief states where evidence is insufficient rather than forcing a verdict.

Do **not** start researching yet. Frame first.
