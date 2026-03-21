# KORUM OS - REPORT TEMPLATE

## PURPOSE

This document defines the canonical Korum report output.

It is not a cosmetic layout guide.

It is the rendering contract between:

- the mission prompt
- the engine output
- the exported decision artifact

## CORE RULE

The report must be filled by named decision slots.

The system must not generate a freeform report and style it afterward.

Prompt structure drives report structure.

## TEMPLATE POSITION IN THE STACK

The report template exists downstream of:

- `DNA.MD`
- `CONTROL_LAYER.MD`
- `DECISION_PACKET.MD`
- prompt contract

The report is the visible form of the decision packet.

## PRIMARY TEMPLATE RULE

Korum reports must lead with a conclusion, not a label.

Do not open with a generic title such as:

- Financial Report
- Strategy Report
- Market Analysis

The first visible sentence must communicate the decision.

## PROMPT BINDING RULE

The prompt must populate named output slots.

It must not request:

- a general report
- a polished summary
- a narrative analysis

It must request a structured decision artifact.

### Required Prompt Outcome

The prompt should produce the following blocks in order:

1. Decision Call
2. Score and Status
3. Why It Wins
4. Top 3 Risks
5. Monday-Morning Actions
6. Council Contributors
7. Node Sections
8. Inline Verification and Challenge
9. Charts near source data
10. Composite Truth Score

## REPORT STRUCTURE

### 1. Decision Call

This is the report headline.

It must:

- be one clear recommendation or decision
- avoid hedging language
- state the main conclusion in plain English

#### Example Shape

Korum-OS remains profitable, but export should be treated as conditional until revenue recognition and cash-flow controls are validated.

### 2. Score and Status

This must appear immediately near the Decision Call.

It must show:

- score from 0 to 100
- status label
- confidence band

#### Allowed Bands

- 80-90 = Recommended
- 70-79 = Conditional
- below 70 = Failed

Soft language such as "moderate-to-high" is not allowed as a substitute.

### 3. Why It Wins

This block explains why the recommendation is the strongest defensible decision.

It must contain:

- 3 to 5 bullets
- only validated or conditionally stated reasoning
- direct connection to data, challenge, or evidence

### 4. Top 3 Risks

This must appear on page 1 or at the first decision surface.

It must:

- list the top 3 failure points
- appear inline, not buried in an appendix
- reflect red-team thinking where relevant

### 5. Monday-Morning Actions

This block answers:

What happens next?

Format:

① Action `(AGENT · Role)`
② Action `(AGENT · Role)`
③ Action `(AGENT · Role)`

Actions must be specific, executable, and assigned.

### 6. Council Contributors

This block shows who contributed to the decision.

Format:

Name · Role · Status

Do not use a large grid or generic bio cards.

### 7. Node Sections

Each node section represents a meaningful decision support unit.

Each node should contain:

- node heading
- key finding
- implication
- recommendation
- provenance line

#### Preferred Shape

Key Finding:
One short paragraph or 2 to 3 bullets

Implication:
One short paragraph

Recommendation:
One short paragraph or numbered action

Provenance:
Origin / challenge path / status

### 8. Inline Verification and Challenge

Verification and challenge must feel like decision pressure, not a footnote.

Use visible blocks for:

- verified claims
- flagged claims
- conditional claims

#### Required Verification Shape

Claim
Status
Challenged by
Why it holds or fails

### 9. Charts Near Source Data

Charts must appear beside or immediately after the data or narrative they support.

Charts must not be grouped into decorative galleries.

Chart titles must express insight, not description.

#### Correct

Revenue is concentrated in subscriptions, increasing dependency risk

#### Incorrect

Subscriptions Drive Majority of Revenue

### 10. Composite Truth Score

This appears near the report end.

It must be:

- visible
- large enough to matter
- paired with a closing statement

## PAGE 1 CONTRACT

The first page is the decision page.

Page 1 must contain:

- Decision Call
- Score and Status
- Why It Wins
- Top 3 Risks
- Monday-Morning Actions
- 3-stat strip

If page 1 reads like a summary blob, the template has failed.

## NARRATIVE RULES

Narrative must support action.

Avoid:

- long unbroken paragraphs
- repeated restatement
- generic financial commentary
- filler transitions

Prefer:

- short paragraphs
- mini headers
- high-signal bullets
- visible implications

## PULL QUOTE RULE

Pull quotes are mandatory when a claim carries strategic, verified, or flagged weight.

### Color Semantics

- Green = verified
- Red = flagged
- Blue = strategic

### Pull Quote Use Cases

Use pull quotes for:

- decisive evidence
- high-risk contradiction
- strategic conclusion
- auditor-style challenge

Do not use pull quotes as decoration.

## PROVENANCE RULE

Every key claim must show:

- origin
- challenge path
- status

Allowed statuses:

- ✓ Verified
- ⚑ Flagged
- ◎ Conditional

If provenance is absent, the claim should not appear as authoritative.

## PROMPT SLOT CONTRACT

The prompt should populate explicit report fields.

### Required Slots

- `decision_call`
- `score`
- `status`
- `confidence_band`
- `why_it_wins`
- `top_risks`
- `monday_actions`
- `contributors`
- `node_sections`
- `verification_blocks`
- `charts`
- `composite_truth_score`

### Prompt Rule

If a slot is missing, the engine should not silently improvise a replacement.

It should:

- mark the slot missing
- reduce confidence where appropriate
- block export if the missing slot is required by the readiness gate

## REPORT FAIL CONDITIONS

The report fails if any of the following are true:

- no clear decision headline
- no visible score and status
- no Why It Wins block
- risks are buried
- actions are missing or vague
- provenance is missing
- chart titles are descriptive instead of insight-based
- charts are detached from their source data
- text appears as a wall instead of a decision artifact
- verification appears as a weak footnote instead of visible challenge

## EXPORT RULE

The exported report must preserve:

- decision hierarchy
- status visibility
- provenance visibility
- chart placement
- action readability

If export flattens the report into a generic document, the template is not compliant.

## TEMPLATE TEST

Before shipping, ask:

- Does page 1 tell me what decision to make?
- Can I see the score and band immediately?
- Can I explain why this wins in under 20 seconds?
- Are the top risks visible without hunting?
- Do I know what happens Monday morning?
- Can I trace each major claim?
- Do the charts clarify a nearby claim?

If any answer is no, the report is not ready.
