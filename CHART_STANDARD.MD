# KORUM OS - CHART STANDARD

## PURPOSE

This document defines the Korum chart system.

Korum does not choose charts based on library convenience.

Korum chooses charts based on decision meaning.

Charts are defined by semantic purpose first.
Renderers are implementation details second.

## CORE RULE

Charts are defined by meaning, not by library.

If a chart does not improve decision clarity, it should not render.

## PRIMARY RENDERING STRATEGY

### Canonical Renderer

Custom SVG is the primary chart renderer.

It is the foundation because it provides:

- full visual control
- reliable export behavior
- precise placement near source data
- strict adherence to Korum color semantics
- reduced dependency on third-party default styling

### Secondary Renderer

Chart.js may be added later as a secondary renderer.

It is allowed only if it obeys the Korum chart standard.

Chart.js is a rendering option.

It is not the source of truth for chart structure, styling, or semantics.

### Mermaid Role

Mermaid is allowed for structural diagrams such as:

- process flow
- orchestration flow
- sequence logic
- system relationships

Mermaid is not the primary renderer for branded analytical charts.

## CHART ABSTRACTION LAYER

All charts must be defined through a semantic chart object before rendering.

The renderer must consume the semantic object rather than inventing chart meaning.

### Example Semantic Shape

```json
{
  "type": "bar",
  "purpose": "comparison",
  "title": "Revenue by Segment",
  "insight": "Enterprise dominates revenue",
  "status": "verified",
  "data": [],
  "provenance_ref": [],
  "notes": []
}
```

### Required Semantic Fields

Every chart definition should include:

- `type`
- `purpose`
- `title`
- `insight`
- `status`
- `data`
- `provenance_ref`

### Optional Semantic Fields

When needed, a chart definition may include:

- `subtitle`
- `annotations`
- `thresholds`
- `comparison_basis`
- `time_horizon`
- `notes`

## CHART TAXONOMY

Korum charts must belong to an allowed decision-purpose class.

### Allowed Purposes

- comparison
- composition
- trend
- threshold
- distribution
- risk

### Allowed Chart Types by Purpose

Comparison:

- bar
- grouped bar
- ranked bar

Composition:

- donut
- stacked bar

Trend:

- line
- area

Threshold:

- bullet
- threshold bar

Distribution:

- histogram
- range band

Risk:

- matrix
- scored heat grid

### Restriction Rule

No chart type should be used outside its decision purpose without explicit justification.

## CHART SEMANTIC RULES

Every chart must express a decision-relevant idea.

### Required Meaning Elements

Each chart must make visible:

- what is being compared or measured
- why it matters
- what insight the user should take away
- whether the underlying claim is verified, conditional, or flagged

### Insight Rule

Every chart must carry an explicit insight statement.

If the chart cannot support a clear insight, remove the chart.

### Provenance Rule

Every chart must link to the source data or source claims that justify it.

If provenance is missing, the chart may not present itself as verified.

## CHART PROXIMITY RULE

A chart must appear beside or immediately after its source data or supporting narrative.

Charts may not be detached from the evidence that explains them.

### Placement Rule

Allowed placements:

- beside the data block
- immediately after the data block
- inline with the decision paragraph when space allows

Disallowed placements:

- report appendix by default
- chart dump at the bottom of a page
- detached visual gallery

### Removal Rule

If a chart cannot be placed near the source data:

- move it closer
- or remove it

## COLOR SEMANTICS

Korum chart color is semantic, not decorative.

### Fixed Meanings

- Blue = structure
- Green = verified
- Red = risk or flagged
- Amber = conditional

### Color Rule

A renderer may not invent extra color meaning without a defined semantic rule.

### Style Rule

Default library palettes are not allowed.

All renderers must map colors through Korum semantic tokens.

## ANNOTATION AND LABELING RULES

Labels exist to support action, not decoration.

### Required Label Behavior

Charts should label:

- primary measure
- category or time axis
- key outlier when present
- threshold when relevant
- insight anchor where useful

### Annotation Rule

Use annotations to highlight:

- decisive variance
- threshold breach
- dominant category
- flagged uncertainty

## STATUS AND CONFIDENCE RULES

Chart status must match decision status.

### Allowed Status States

- verified
- conditional
- flagged

### Status Visibility Rule

Status must be visible in or immediately adjacent to the chart context.

It must not rely on hidden metadata.

### Confidence Rule

If a chart supports a key decision claim, its confidence relationship must be visible through accompanying narrative or status treatment.

## RENDERER CONTRACT

Every renderer must obey the same chart contract.

### Renderer Requirements

Each renderer must:

- accept the semantic chart object
- preserve the same meaning across renderers
- use Korum semantic colors
- support provenance linking
- support export without visual degradation
- avoid default decorative styles

### Renderer Limitations Rule

If a renderer cannot accurately express a required chart meaning, the chart must fall back to a renderer that can.

The standard is primary.
The renderer is replaceable.

## EXPORT RULES

Charts must export cleanly in decision artifacts.

### Canonical Export Form

SVG is the canonical chart export format.

### Export Requirements

Charts must export with:

- legible labels
- preserved color semantics
- stable layout
- visible status context
- proximity to the relevant narrative or data block

### Export Restrictions

Canvas-only output is not the canonical export source.

If a renderer depends on canvas output, it must still support clean artifact export or it does not qualify as compliant.

## ANTI-GENERIC ENFORCEMENT

Korum charts must not look like default dashboard filler.

### Banned Outcomes

- random decorative gradients
- default library styles
- chart clutter without insight
- oversized legends replacing narrative
- charts used where one sentence would be clearer
- multiple charts repeating the same conclusion

### Meaning Test

Before rendering, ask:

- What decision does this chart support?
- What insight does it add that text alone does not?
- Is its status clear?
- Is its source visible?

If those answers are weak, do not render the chart.

## FAILURE CONDITIONS

A chart fails the standard if any of the following are true:

- no clear purpose
- no explicit insight
- no provenance reference
- detached from source data
- decorative color use
- default renderer styling
- redundant with nearby content
- weak export fidelity

Failed charts should be revised or removed.

## IMPLEMENTATION DIRECTIVE

We are not choosing a chart library.

We are defining a chart system.

Libraries are interchangeable.

Standards are not.
