# KORUM OS — Architecture Vision

### Decision Governance Runtime
### March 2026

---

## Core Identity (One-Liner)

> "Korum OS separates thinking into roles, enforces evidence before conclusions, and governs decisions like a system — not a model."

---

## What KORUM OS Actually Is

KORUM OS is **not an AI system**. It is a **decision governance runtime**.

Most systems do this:
```
DATA → AI → ANSWER
```

KORUM does this:
```
DATA → ROLES → CONFLICT → VALIDATION → GATE → OUTPUT
```

**This is the moat.** Anyone can call an LLM. Nobody is enforcing:
- Role conflict (adversarial by design)
- Evidence thresholds (Governor calibration)
- Decision gating (diagnostic-first, Red Team override)

---

## Role Architecture: Same Role, Different Verticals

Roles are **behavioral contracts**, not personas. The same role operates across every vertical — only the **target logic** changes based on DNA.

### LOKI (Adversarial / Anti-Forensic Detection)

| Vertical | LOKI Function |
|----------|---------------|
| Cyber | Detect log tampering, Living-off-the-Land (LotL) techniques |
| Finance | Detect cherry-picked data, selective disclosure |
| Telecom | Detect misleading telemetry, masked outages |
| Compliance | Detect narrative manipulation, regulatory spin |

### ODIN (Orchestration / Timeline Reconstruction)

| Vertical | ODIN Function |
|----------|---------------|
| Cyber | Attack chain timeline reconstruction |
| Finance | Transaction flow orchestration |
| Telecom | Outage cascade sequencing |
| Compliance | Regulatory event ordering |

### MIMIR (State Verification / Historical Precedent)

| Vertical | MIMIR Function |
|----------|----------------|
| Cyber | Immutable state comparison (before/after breach) |
| Finance | Historical precedent matching |
| Telecom | Baseline telemetry comparison |
| Compliance | Prior ruling / enforcement matching |

**Key principle:**
- Roles don't change
- Their behavioral rules do
- DNA drives role behavior

---

## DNA Drives Role Behavior

### Forensic DNA (Cyber Vertical)
```
LOKI = aggressive, adversarial, zero trust
ODIN = timeline reconstruction
MIMIR = immutable state comparison
```

### Strategy DNA (Future)
```
LOKI = assumption challenger
ODIN = decision orchestrator
MIMIR = historical precedent engine
```

---

## Vertical = Data + Ontology + Constraints

A vertical is NOT a UI or a feature set. A vertical IS:
- A **data model** (what entities exist)
- A **vocabulary** (domain language)
- **Constraints** (what evidence is required)

### Cyber Vertical Ontology
```json
{
  "entities": ["user", "machine", "token", "process"],
  "events": ["login", "execution", "network_connection"],
  "relationships": ["initiated_by", "executed_on", "authenticated_via"],
  "data_sources": ["splunk", "ad_logs", "netflow"]
}
```

### Telecom Vertical Ontology
```json
{
  "entities": ["node", "circuit", "customer", "technician"],
  "events": ["latency_spike", "packet_loss", "dispatch"],
  "relationships": ["connected_to", "serves", "assigned_to"],
  "data_sources": ["snmp", "noc_metrics", "field_reports"]
}
```

### Finance Vertical Ontology (Draft)
```json
{
  "entities": ["account", "transaction", "counterparty", "instrument"],
  "events": ["trade", "settlement", "variance", "audit_flag"],
  "relationships": ["funded_by", "authorized_by", "settled_through"],
  "data_sources": ["ledger", "statements", "regulatory_filings"]
}
```

### Defense Vertical Ontology (Draft)
```json
{
  "entities": ["asset", "threat", "sector", "unit", "sensor"],
  "events": ["detection", "engagement", "maneuver", "comms_intercept"],
  "relationships": ["assigned_to", "detected_by", "operating_in"],
  "data_sources": ["isr_feeds", "sigint", "field_reports", "telemetry"]
}
```

**The engine doesn't care what the domain is. It processes structured reality.**

---

## BUILD PLAN — 4 Steps

### Step 1: Role Registry (JSON/YAML)

```yaml
LOKI:
  function: anti_forensic_detection
  can_conclude: false
  can_block: true
  behavior_driver: DNA

ODIN:
  function: timeline_orchestration
  can_conclude: true
  requires: [MIMIR, LOKI]
  behavior_driver: DNA

MIMIR:
  function: state_verification
  can_conclude: false
  provides: [baseline_comparison, historical_precedent]
  behavior_driver: DNA
```

### Step 2: DNA Profiles

```yaml
forensic_hunter:
  posture: zero_trust
  evidence_threshold: high
  allow_recommendations: false
  diagnostic_first: true
  governor_floor: 75
  red_team: always_on

predictive_sentinel:
  posture: proactive_defense
  evidence_threshold: moderate
  allow_recommendations: true
  diagnostic_first: false
  governor_floor: 65
  red_team: always_on

operational_assessment:
  posture: balanced_analysis
  evidence_threshold: moderate
  allow_recommendations: true
  diagnostic_first: conditional
  governor_floor: 60
  red_team: on_request
```

### Step 3: Vertical Adapters

```
Cyber adapter   → Splunk logs, AD logs, netflow
Telecom adapter → SNMP metrics, NOC data, field tickets
Finance adapter → Ledger data, statements, filings
Defense adapter → ISR feeds, SIGINT, sensor telemetry
```

### Step 4: Engine Flow (Real Logic)

```python
for role in active_roles:
    role_output = execute(role, dna, vertical_data)

conflicts = analyze_conflicts(role_outputs)

gate_result = diagnostic_gate(role_outputs, conflicts)

if gate_result == "FAIL":
    return investigation_packet
else:
    return decision_packet
```

---

## NEXT LEVEL — Role Interdependency Graph

### Authority Resolution Rules

```
ODIN cannot conclude unless:
  - MIMIR validates (state comparison confirms)
  - LOKI does NOT block (no evidence tampering detected)

LOKI can block at any time:
  - If evidence integrity fails → entire pipeline pauses
  - Governor must acknowledge block before proceeding

MIMIR provides but never decides:
  - Supplies baseline comparisons
  - Flags deviations from historical norms
  - Cannot issue recommendations
```

### Current Implementation Mapping

| Architecture Role | Current KORUM Implementation |
|---|---|
| ODIN (orchestrator) | Council synthesis + Governor |
| LOKI (adversarial) | Red Team pass |
| MIMIR (state verification) | Truth Scoring + Evidence Classification |
| Diagnostic Gate | `_requires_diagnostic_first()` + Governor score floor |
| Role interdependency | Red Team override → forces diagnostic-first (shipped) |

---

## NEXT LEVEL — Evidence Graph (The "Palantir Moment")

### Concept
```
Nodes: [TARGET_A], [TOKEN_X], [HOST_Y]
Edges: authenticated_to, executed_on
```

### What This Becomes
- **Visual engine** — render attack chains, decision trees, entity relationships
- **Forensic reconstruction** — see exactly how entities connect
- **Export artifact** — evidence graphs in reports (SVG/PNG)
- **Interactive in UI** — click nodes to see source evidence

### Implementation Path
1. Extract entities + relationships from council output
2. Build graph data structure (nodes + edges)
3. Render via D3.js or similar in frontend
4. Export as SVG artifact → rides into Word/PDF via existing chart pipeline

---

## COMPETITIVE MOAT SUMMARY

| What Others Do | What KORUM Does |
|---|---|
| Call an LLM | Enforce role conflict |
| Generate answers | Gate decisions on evidence |
| Trust model output | Red Team challenges everything |
| Black box reasoning | Hash-chained audit trail |
| Single perspective | Five adversarial perspectives |
| Hope for accuracy | Govern for integrity |

---

*Architecture vision document. Implementation details in engine_v2.py, vertical configs in VERTICAL_STRATEGY.md, roadmap in FUTURE_IDEAS.md.*
