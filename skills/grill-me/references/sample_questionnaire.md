# Search UI Improvement Plan: Grill-Me Questionnaire Sample

## Overview

- **Purpose:** Expose assumptions, risks, and decision dependencies before implementing a search UI improvement.
- **File workflow:** Append every round to this file. Never overwrite answers from earlier rounds.
- **How to answer:** Enter a number or free-text answer after `Answer:`. If unsure, choose the recommended option.

---

## Round 1: Test Initial Assumptions

- **Round purpose:** Establish the target outcome, initial audience, and permitted scope.
- **Connection from the previous round:** None; this is the first round.
- **Questions:** 3

### R1-Q1: Success Metric

Which outcome matters most?

1. Increase the rate at which searchers reach their intended page (Recommended | Measures whether search produces a useful outcome)
2. Increase search-result click-through rate (Alternative | Easy to measure but does not prove post-click satisfaction)
3. Reduce the zero-results rate (Alternative | Useful but may require changes beyond the UI)
4. Let the agent decide / Use the recommendation

Answer: 1

Rationale / Notes (optional): The final outcome should be whether users reach the page they need.

---

### R1-Q2: Initial Audience

Which users should the first release optimize for?

1. New and occasional users (Recommended | They benefit most from clearer search behavior)
2. Existing frequent users (Alternative | Efficiency gains are possible, but workflow changes may be disruptive)
3. Administrators and internal operators (Alternative | Valuable for operations but likely requires a separate design)
4. Let the agent decide / Use the recommendation

Answer: 1

Rationale / Notes (optional): We suspect first-time users abandon search frequently.

---

### R1-Q3: Change Scope

What may this effort change?

1. Search input, suggestions, and results UI only (Recommended | Keeps the experiment attributable to UI changes)
2. UI plus ranking logic (Alternative | May deliver more value but mixes two causes)
3. The entire path through result-detail pages (Alternative | Broader impact but likely to expand scope)
4. Let the agent decide / Use the recommendation

Answer: 2

Rationale / Notes (optional): Poor ranking may be part of the problem.

---

## Round 2: Separate Scope and Experiment Effects

- **Round purpose:** Resolve the conflict between a UI-focused project and the desire to change ranking.
- **Connection from the previous round:** R1-Q1 selected destination-page reach as the outcome, while R1-Q3 included ranking changes. Combining both prevents attribution.
- **Questions:** 3

### Question Path

| Starting point | Unresolved issue | Current question |
| --- | --- | --- |
| R1-Q1 | The outcome depends on UI and ranking quality | R2-Q1 |
| R1-Q3 | UI and ranking changes share one scope | R2-Q1, R2-Q2 |
| R1-Q3 | No stopping rule exists | R2-Q3 |

### R2-Q1: Experiment Unit

Should UI and ranking changes be tested together?

1. Test them separately (Recommended | Preserves causal attribution and supports the next decision)
2. Test them together from the start (Alternative | Faster but obscures the cause of improvement or regression)
3. Test UI first and defer ranking (Alternative | Lower risk, but limited if ranking is the root problem)
4. Let the agent decide / Use the recommendation

Answer:

Rationale / Notes (optional):

---

### R2-Q2: Ranking Change Limit

How much ranking change is acceptable in this effort?

1. Minor weight adjustments only (Recommended | Tests the ranking hypothesis with limited risk)
2. Replace the ranking model (Alternative | Larger upside but much higher validation and rollback cost)
3. Limit changes to synonyms and spelling normalization (Alternative | Helps zero-result searches but not ranking quality)
4. Let the agent decide / Use the recommendation

Answer:

Rationale / Notes (optional):

---

### R2-Q3: Stopping Rule

When should the experiment stop?

1. Intended-page reach fails to improve while post-search abandonment worsens (Recommended | Covers both the primary outcome and a harmful side effect)
2. Search-result click-through rate decreases (Alternative | Detects change quickly but may misclassify fewer, better clicks)
3. Support complaints cross a defined threshold (Alternative | Captures harm but needs a threshold in advance)
4. Let the agent decide / Use the recommendation

Answer:

Rationale / Notes (optional):
