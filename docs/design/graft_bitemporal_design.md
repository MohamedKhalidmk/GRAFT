# Time in the graph: bitemporal facts (design, 2026-11-22)

> Idea from the user, 2026-11-22. New candidate **G46** in the [registry](../reference/REGISTRY.md). Built only after writer v2's
> dev results (G41/G42, [plan](graft_longmemeval_plan_design.md)), on the better writer arm.

## Question

LongMemEval's temporal-reasoning questions ("how many days between ...", "which happened first", "how long ago")
ask when something happened, which is often not when it was said. GRAFT keeps one order today: the arrival order of
facts (serial numbers on FactConsolidation, session order on LongMemEval). Does storing both times, and using the
right one for each job, answer temporal questions better without hurting anything else?

## Two times per fact

| Time | Meaning | Source | Used for |
|---|---|---|---|
| **Said time** | when the fact was recorded | LongMemEval: the session's date (from the chunk header); FactConsolidation: the fact's serial number (as now) | supersede: a newer statement replaces an older one by said time, exactly as today |
| **Event time** | when the thing happened | the writer, when the text gives a time: "last Tuesday" resolved against the session date to an absolute date (writer v2 already asks for this); empty when the text gives none | temporal questions and the guide's planning |

- Stored on every fact's provenance: `said_time` (ISO date or serial) and `event_time` (ISO date, or a date range for
  "in March"), plus `event_time_source` ("text" when stated, "said" when it falls back to the said time).
- The writer returns `event_time` as its own JSON field instead of folding the date into the object, so the object
  stays comparable across revisions (supersede still matches subject + relation).
- Supersede is unchanged and uses said time; event time never decides which version is current.

## Using event time

1. **Display:** each fact shown to the answering model carries both times: `[said 2023/05/20 | happened 2023/05/13]`.
2. **Temporal questions:** a question with a temporal cue (first, before, after, ago, how many days/weeks/months,
   since, when) gets its retrieved facts ordered by event time (said time where there is no event time) before they are
   shown, and the question date stays in the prompt.
3. **Planning:** when the guide follows a relation chain and two candidate facts disagree, the one with the later said
   time wins (as now); event time only orders the chain's facts for the answer.

## Test

- **LongMemEval temporal-reasoning dev items** (20 of the 76): G46 against its parent (the better of G41/G42), the same
  day, Qwen, the Memory route's base route Fast, judged by Haiku with the official prompt. Also reported: how many facts
  carry a stated event time, and gold-in-50 for these items.
- **FactConsolidation retest, the same day as G35:** FactConsolidation's facts carry serial numbers and no event times,
  so G46 must equal G35 there within the repeat spread (the keep rule's second half).
- **Keep rule (user, set 2026-11-22):** keep G46 if it beats its parent by more than the repeat spread on the temporal
  items, and FactConsolidation does not drop by more than the spread.

## Cost

Free (Qwen). The build is a writer-prompt change, so G46 needs its own build of the 76 dev histories (and of the
FactConsolidation graph on Qwen). A full rebuild of all 500 histories waits for the user's yes, as every rebuild does.
