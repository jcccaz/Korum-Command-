# KORUM OS - CONTROL LAYER

## PURPOSE

This document defines the operating control system above the Korum engine.

It exists to prevent drift, uncontrolled execution, weak exports, and false decision authority.

DNA defines what Korum is.

The Control Layer defines when Korum may proceed, what it must validate, when it must stop, and what may leave the system.

## CORE RULE

The engine does not self-govern.

The Control Layer governs:

- intake
- validation
- progression
- retry logic
- challenge escalation
- export permission
- outcome review

## GOVERNANCE MODEL

### Human Governor

The human is the governor of progression.

The system may recommend:

- proceed
- retry
- escalate
- block export

The system may NOT grant itself final authority where human review is required.

### Phase Advancement Rule

No phase advances unless its required output exists and passes the gate for that phase.

If a required artifact is missing, incomplete, contradictory, or unsupported:

- phase advancement is blocked
- the system must return the blocking reason
- the blocking reason must be visible to the user

### Override Rule

Override is allowed only through explicit human action.

If a human overrides a block:

- the override must be recorded
- the blocked condition must remain visible
- export status must reflect the override condition

## 1. PREFLIGHT INTAKE

Preflight intake is mandatory before the engine begins.

Its purpose is to prevent ambiguous missions from entering the decision system.

### Mission Card Requirements

Every run must begin with a Mission Card containing:

- mission question
- decision type
- objective
- time horizon
- target user or owner
- constraints
- known risks
- required output type
- available evidence inputs

### Preflight Validation

The system must validate:

- the mission is decision-oriented, not open-ended brainstorming
- the objective is specific enough to evaluate
- the decision horizon is known
- constraints are stated or explicitly marked missing
- evidence inputs are present or explicitly insufficient

### Preflight Outcomes

Preflight may return only one of the following:

- Pass
- Conditional Pass
- Fail

#### Pass

Use when the mission is sufficiently defined to begin reasoning.

#### Conditional Pass

Use when the mission can proceed but missing inputs reduce confidence.

The missing inputs must be named explicitly.

#### Fail

Use when the mission is too ambiguous or underspecified to support a defensible decision.

A failed preflight must not enter the engine.

## 2. EVIDENCE RULES

Evidence quality directly affects confidence, provenance status, and decision readiness.

### Evidence Classes

The system must classify evidence into one of the following:

- Verified
- Conditional
- Flagged
- Rejected

### Verified

Use when the claim is supported by reliable source material, attributable origin, and no unresolved contradiction.

### Conditional

Use when the claim is plausible and supported in part, but material uncertainty remains.

The missing condition must be named.

### Flagged

Use when the claim is contested, stale, weakly sourced, or materially vulnerable to challenge.

### Rejected

Use when the claim cannot support a decision artifact.

Rejected claims may not be presented as decision support.

### Evidence Validation Rules

Each key claim must show:

- origin
- evidence basis
- freshness when relevant
- contradiction status
- provenance status

If a key claim lacks provenance, it may not be treated as verified.

If two claims materially conflict, the conflict must be surfaced rather than silently averaged away.

## 3. DECISION READINESS GATE

No artifact ships unless it passes the Decision Readiness Gate.

### Required Conditions

Every output must include:

- one clear decision call
- confidence score
- confidence band
- why it wins
- top risks inline
- Monday-morning action plan
- provenance for key claims
- visible status

### Gate Logic

If any required condition is missing:

- gate fails
- export is blocked

If the output uses hedging in place of a decision:

- gate fails
- output must be revised

If the output is formatted as generic summary instead of decision artifact:

- gate fails
- output must be revised

## 4. FAIL / RETRY LOGIC

Retry logic is mandatory when the decision score is below threshold or key challenges remain unresolved.

### Score Thresholds

- 80-90: Recommended
- 70-79: Conditional
- below 70: Fail

### Retry Rule

If score is below 80:

- re-run Critic
- re-run Assembler
- strengthen weak claims
- surface unresolved gaps

### Fail Rule

If score remains below 70 after retry:

- artifact fails
- export is blocked
- system must state why confidence is insufficient

### Deadlock Rule

If repeated critique cycles do not materially improve decision confidence:

- system enters deadlock state
- deadlock reason must be displayed
- human governor must choose:
  - stop
  - revise mission
  - provide more evidence
  - force conditional review

The engine may not loop indefinitely.

## 5. RED TEAM TRIGGER RULES

Red Team may be optional for low-stakes runs and mandatory for high-stakes runs.

### Mandatory Triggers

Red Team is required when any of the following are true:

- high financial impact
- legal or regulatory exposure
- safety implications
- reputational exposure
- strategic one-way decision
- sparse or conflicting evidence
- user explicitly requests challenge

### Optional Triggers

Red Team may run when:

- confidence is near threshold
- the recommendation depends on a narrow assumption
- the mission contains obvious downside asymmetry

### Red Team Output Requirements

Red Team must produce:

- top failure modes
- broken assumptions
- attack path on recommendation
- confidence impact

Red Team must not rewrite the final output directly.

It challenges. It does not assemble.

## 6. EXPORT GATE

Export is a privilege, not a default action.

### Export Requirements

An artifact may export only if:

- preflight passed or conditionally passed with visible limitations
- readiness gate passed
- provenance is visible
- confidence is visible
- top risks are visible
- status stamp is visible

### Export Blocks

Export must be blocked if:

- score is below 70
- no clear decision exists
- provenance is missing
- major evidence conflict is hidden
- action plan is missing
- output is generic or decorative

### Export Status Types

Every export must carry one of the following statuses:

- Recommended
- Conditional
- Failed
- Overridden

Failed artifacts may not export as decision-ready output.

If overridden by a human, the export must carry the override state visibly.

## 7. OUTCOME REVIEW LOOP

Korum must not end at export.

The system must support review of whether the decision was correct, effective, and properly scoped.

### Outcome Review Inputs

Outcome review should capture:

- what decision was made
- what action was taken
- what result occurred
- what assumptions proved correct
- what assumptions failed
- whether confidence was calibrated correctly

### Outcome Review Purpose

Outcome review exists to:

- improve calibration
- identify repeated failure patterns
- improve blueprint quality
- improve evidence weighting

### Outcome Review Rule

A completed run should remain reviewable after execution.

The system must preserve enough state to compare:

- recommendation
- rationale
- risks
- provenance
- eventual outcome

## 8. STATE AND PERSISTENCE RULES

The control state of a run must be visible and recoverable.

### Required Run State

Each run should preserve:

- mission card
- phase status
- evidence status
- challenge log
- score state
- export state
- override state
- outcome review state

### Resume Rule

A resumed run must continue from a known visible state.

The system must not silently discard prior challenge, provenance, or gate status.

### Revision Rule

If the mission changes materially:

- prior decision state must not be treated as current by default
- the run must be marked revised
- confidence should be recalculated

## 9. HUMAN-IN-THE-LOOP REQUIREMENT

Korum supports decision-making.

It does not simulate unearned authority.

### Human Control Points

Human review should be available at:

- preflight completion
- red-team escalation
- deadlock state
- export approval
- outcome review

### Non-Negotiable Rule

If the system cannot explain why a decision should be trusted, it must not behave as if it has earned trust.

## CONTROL LAYER TEST

Before implementation or export, ask:

- Is the mission valid enough to enter the engine?
- Is the evidence strong enough to support a decision?
- Has the recommendation been challenged hard enough?
- Is confidence high enough to justify action?
- Is the output safe and honest to export?
- Can a human see why the system proceeded?

If any answer is no, the Control Layer has not been satisfied.
