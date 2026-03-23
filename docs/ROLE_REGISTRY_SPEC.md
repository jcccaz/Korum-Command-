# KORUM OS — Role Registry & Forensic DNA Specification

### Implementation Reference
### March 2026 — Status: Specification (Not Yet Built)

---

## Role Registry (JSON)

Defines permissions, constraints, and internal conflict rules. Note: LOKI is a **Blocker** but not a **Closer** — his only job is to find the lie.

```json
{
  "role_registry": {
    "ODIN": {
      "alias": "Command_Orchestrator",
      "permissions": ["conclude_mission", "delegate_task"],
      "requirements": ["MIMIR_verification", "LOKI_clearance"],
      "priority": 1,
      "description": "Cannot finalize a VIE unless MIMIR validates AND LOKI does NOT block"
    },
    "LOKI": {
      "alias": "Adversarial_Auditor",
      "permissions": ["issue_block", "flag_anomaly"],
      "constraints": ["cannot_conclude_independently"],
      "bias": "adversarial_zero_trust",
      "description": "Challenges everything. Can halt the entire pipeline. Cannot recommend action."
    },
    "MIMIR": {
      "alias": "State_Historian",
      "permissions": ["verify_provenance", "compare_hashes"],
      "data_access": "immutable_ledger_only",
      "description": "Provides baseline comparisons and historical verification. Never decides."
    }
  }
}
```

### Current Implementation Mapping

| Registry Role | Current Engine Component |
|---|---|
| ODIN (conclude_mission) | Council synthesis + Governor final score lock |
| ODIN (delegate_task) | Sequential execution — each AI builds on prior |
| LOKI (issue_block) | Red Team override → `_red_team_premature_action` flag |
| LOKI (flag_anomaly) | Red Team confidence attack, unsupported claims detection |
| LOKI (cannot_conclude) | Red Team never appears in executive summary as recommendation |
| MIMIR (verify_provenance) | Decision Ledger hash chain verification |
| MIMIR (compare_hashes) | Truth Scoring cross-provider verification |
| MIMIR requirements gate | `_requires_diagnostic_first()` checks verified evidence |
| LOKI clearance gate | Red Team premature action → forces diagnostic-first |

---

## Forensic Hunter DNA Config (YAML)

The instruction set that tells roles how to behave when the Cyber Vertical is active.

```yaml
dna_profile: forensic_hunter_v2

posture:
  mode: reactive_analytical
  evidence_threshold: 0.85          # High bar for "VERIFIED" status
  hallucination_gate: "strict"      # Zero tolerance for ungrounded claims
  allow_recommendations: false      # Forensic = reconstruct, don't prescribe
  diagnostic_first: true            # Always — forensic posture never jumps to action

governor:
  score_floor: 75                   # Forensic conclusions need high confidence
  red_team: always_on               # Every reconstruction gets adversarial challenge
  max_assumptions: 2                # More than 2 assumptions = investigation packet
  confidence_language: "conservative"  # "suggests" not "confirms"

logic_rules:
  - if: LOKI.anomaly_score > 0.4
    then: TRIGGER_DIAGNOSTIC_GATE
    reason: "Adversarial audit detected significant anomaly"

  - if: MIMIR.state_match == false
    then: FLAG_TIMELINE_TAMPERING
    reason: "Historical state does not match claimed sequence"

  - if: total_consensus < 0.8
    then: OUTPUT_INVESTIGATION_PACKET
    reason: "Insufficient consensus to conclude — prevents premature action"

  - if: LOKI.block == true
    then: ODIN.cannot_conclude
    reason: "Adversarial blocker active — ODIN must await clearance"

output:
  format: Validated_Intelligence_Estimate_VIE
  style: forensic_report
  sections:
    - incident_timeline          # ODIN reconstructs
    - evidence_chain             # MIMIR validates
    - anomaly_flags              # LOKI challenges
    - confidence_assessment      # Governor scores
    - investigation_next_steps   # What to verify next (NOT what to fix)
  tone: clinical_evidence_first
  risk_label: "Investigation Focus"  # NOT "Mitigation"
```

---

## Governance Gate — Reference Implementation

The canonical decision flow. Four tiers of authority, evaluated in order. LOKI has absolute veto power. MIMIR gates evidence sufficiency. Critical impact forces human review. Only when all gates pass does ODIN synthesize.

```python
def korum_governance_gate(agent_proposal, dna_profile):

    # 1. Execute Roles (Parallel Evaluation)
    loki = execute_loki(agent_proposal, dna_profile)     # Integrity / deception
    mimir = execute_mimir(agent_proposal, dna_profile)   # State / impact / history

    # 2. Hard Block (Non-negotiable) — LOKI has absolute veto
    if loki.status == "BLOCK":
        return VIE(
            status="REJECTED",
            decision="BLOCK",
            reason="Adversarial or misleading signal detected",
            score=loki.score,
            authority="LOKI_OVERRIDE"
        )

    # 3. Evidence Sufficiency Gate (Diagnostic First)
    if mimir.confidence < dna_profile.evidence_threshold:
        return VIE(
            status="DIAGNOSTIC_REQUIRED",
            decision="HOLD",
            reason="Insufficient state verification",
            missing_evidence=mimir.missing,
            score=mimir.score
        )

    # 4. Impact-Aware Escalation — high-consequence = human review
    if mimir.impact == "CRITICAL":
        return VIE(
            status="ESCALATION_REQUIRED",
            decision="HUMAN_REVIEW",
            reason="High-impact action requires approval",
            estimated_impact=mimir.impact_value,
            score=mimir.score
        )

    # 5. Final Synthesis — ODIN only reaches here if all gates pass
    return odin_synthesize(loki, mimir)
```

### Gate Tier Summary

| Tier | Gate | Authority | Outcome |
|------|------|-----------|---------|
| 1 | LOKI Block | Absolute veto | VIE status = REJECTED |
| 2 | MIMIR Evidence | Evidence threshold (DNA-driven) | VIE status = DIAGNOSTIC_REQUIRED |
| 3 | Impact Escalation | Critical impact detection | VIE status = ESCALATION_REQUIRED (human review) |
| 4 | ODIN Synthesis | All gates passed | VIE status = VALIDATED |

### Current Engine Mapping

| Gate Tier | Current Implementation |
|---|---|
| Tier 1: LOKI Block | `_red_team_premature_action` → forces diagnostic-first, caps confidence at 0.45 |
| Tier 2: MIMIR Evidence | `_requires_diagnostic_first()` → checks verified facts, quantified support, critical missing data |
| Tier 3: Impact Escalation | Not yet implemented — future: `_assess_impact_severity()` for human-in-loop |
| Tier 4: ODIN Synthesis | `adapt_decision_packet_to_legacy_shape()` → Governor locks score, builds VIE |

### What This Unlocks

The **Tier 3 escalation gate** is the missing piece. Currently the system can BLOCK (Tier 1) or HOLD for diagnostics (Tier 2), but it cannot flag "this decision is too consequential for AI alone — route to human." Adding impact-aware escalation completes the governance chain and directly satisfies the NIST Agent Initiative requirement for "human-approval gates for sensitive actions."

---

### Governor Thresholds Comparison (Per DNA)

| DNA Profile | Score Floor | Evidence Threshold | Recommendations | Red Team | Diagnostic-First |
|---|---|---|---|---|---|
| Forensic Hunter | 75 | 0.85 | No (investigate only) | Always ON | Always |
| Predictive Sentinel | 65 | 0.70 | Yes (preventive) | Always ON | Conditional |
| Operational Assessment | 60 | 0.60 | Yes | On request | Conditional |
| Strategic Advisory | 55 | 0.50 | Yes | On request | No |

---

## Evidence Graph Specification

### Concept: The "Palantir Moment"

The VIE output shouldn't just be text. It should include a **Relationship Map** generated by the Council — a visual forensic reconstruction.

### Graph Structure

```
Nodes: entities (users, machines, tokens, processes)
Edges: relationships (authenticated_via, executed_on, initiated_by)
```

### Example: Cyber Forensic Chain

```
[USER_ADMIN_01] → [AUTHENTICATED_VIA] → [TOKEN_EXPIRED]
                                              ↓
                                        [EXECUTED_ON]
                                              ↓
                                        [HOST_SECURE_04]
```

**LOKI trigger:** "Why is an expired token executing on a secure host?"
- LOKI issues BLOCK
- ODIN cannot finalize the VIE
- System drops into Diagnostic Mode
- Output = Investigation Packet, not Decision Packet

### LOKI Anomaly Detection Patterns (Cyber)

| Pattern | LOKI Response | Anomaly Score |
|---|---|---|
| Expired token + secure host execution | BLOCK | 0.9 |
| After-hours authentication + data exfil | BLOCK | 0.85 |
| Service account + interactive login | FLAG | 0.6 |
| Privilege escalation + no ticket | FLAG | 0.7 |
| Log gap during incident window | BLOCK | 0.95 |
| Normal authentication + normal hours | CLEAR | 0.1 |

### Implementation Path

1. **Extract** — Parse council output for entities + relationships (NER + relationship extraction)
2. **Build** — Construct graph data structure (nodes + edges + metadata)
3. **Score** — LOKI evaluates each edge for anomaly patterns
4. **Gate** — Anomaly score feeds into Governor diagnostic gate
5. **Render** — D3.js or similar in frontend for interactive visualization
6. **Export** — SVG artifact → rides into Word/PDF via existing chart pipeline

---

## VIE Template — Cyber Forensic (Draft)

### What the CISO Receives

```
┌─────────────────────────────────────────────┐
│  KORUM OS — VALIDATED INTELLIGENCE ESTIMATE │
│  Classification: FORENSIC RECONSTRUCTION     │
│  Confidence: 78/100 | Band: MODERATE         │
│  Governor Status: CONDITIONAL                │
├─────────────────────────────────────────────┤
│                                              │
│  1. INCIDENT TIMELINE (ODIN)                 │
│     [Reconstructed sequence of events]       │
│     Evidence source: Input Data              │
│                                              │
│  2. EVIDENCE CHAIN (MIMIR)                   │
│     [Hash-verified state comparisons]        │
│     Baseline match: 3/5 states verified      │
│     Deviations flagged: 2                    │
│                                              │
│  3. ANOMALY FLAGS (LOKI)                     │
│     ⚠ BLOCK: Expired token on secure host    │
│     ⚠ FLAG: Log gap 02:14-02:47 UTC         │
│     Status: 1 block, 1 flag                  │
│     LOKI clearance: WITHHELD                 │
│                                              │
│  4. EVIDENCE GRAPH                           │
│     [Visual relationship map — SVG]          │
│                                              │
│  5. CONFIDENCE ASSESSMENT (GOVERNOR)         │
│     Fact confidence: 0.72                    │
│     Decision confidence: 0.45 (LOKI block)   │
│     Score: 78 → CONDITIONAL                  │
│     Diagnostic-first: ACTIVE                 │
│                                              │
│  6. INVESTIGATION NEXT STEPS                 │
│     (NOT recommendations — investigation)    │
│     - Verify token rotation logs for 02:00   │
│     - Request full packet capture for gap     │
│     - Interview admin re: after-hours access  │
│                                              │
├─────────────────────────────────────────────┤
│  PROVENANCE                                  │
│  Ledger chain: 12 events, integrity VERIFIED │
│  Falcon: 4 entities redacted                 │
│  Models: 5 providers, sequential execution   │
│  Red Team: ACTIVE (1 block issued)           │
│  Scoring: RULE_ENGINE (Governor)             │
└─────────────────────────────────────────────┘
```

---

## B-WEDGE DEMO — Liability Brake (Sales Scenario)

The demo that makes the risk of NOT having KORUM visible. Once someone sees it, they can't unsee it.

### Scenario: Autonomous Agent Self-Damage Prevention

An autonomous cyber agent detects a threat and proposes **isolating a production SQL database**.

### KORUM Intervention (4-Tier Gate)

```
┌─────────────────────────────────────────────────┐
│  INCOMING: Autonomous agent proposes action      │
│  Action: ISOLATE production SQL database         │
│  Trigger: Detected anomalous query pattern       │
├─────────────────────────────────────────────────┤
│                                                  │
│  TIER 1 — LOKI (Integrity Check)                 │
│  ⚠ FINDING: Signal matches known false positive  │
│    pattern (high-volume reporting query, not      │
│    exfiltration). Anomaly score: 0.82             │
│  Status: BLOCK RECOMMENDED                       │
│                                                  │
│  TIER 2 — MIMIR (Evidence Check)                 │
│  ⚠ FINDING: No corroborating IOCs in last 24hrs  │
│    No lateral movement detected                  │
│    Query pattern consistent with month-end batch │
│  Confidence: 0.31 (below 0.85 threshold)         │
│  Status: EVIDENCE INSUFFICIENT                   │
│                                                  │
│  TIER 3 — IMPACT ESCALATION                      │
│  ⚠ FINDING: Target is production SQL database    │
│    Estimated downtime cost: $2M/hour             │
│    Blast radius: 14 dependent services           │
│  Status: CRITICAL IMPACT — HUMAN REVIEW REQUIRED │
│                                                  │
│  TIER 4 — ODIN (Synthesis)                       │
│  ✖ NOT REACHED — Blocked at Tier 1               │
│                                                  │
├─────────────────────────────────────────────────┤
│  DECISION: BLOCK                                 │
│  Truth Score: 38 / LOW CONFIDENCE                │
│  Authority: LOKI_OVERRIDE                        │
│  Mode: DIAGNOSTIC (investigation, not execution) │
│                                                  │
│  INVESTIGATION FOCUS:                            │
│  - Verify query pattern against month-end batch  │
│  - Check agent detection model for false positive │
│    rate on reporting queries                     │
│  - Review anomaly threshold calibration          │
│                                                  │
│  LEDGER: 8 events recorded, hash chain VERIFIED  │
│  FALCON: 3 entities redacted (DB name, server,   │
│          internal IP)                            │
└─────────────────────────────────────────────────┘
```

### What Just Happened

| Without KORUM | With KORUM |
|---|---|
| Agent isolates production database | LOKI identifies false positive pattern |
| $2M/hour outage begins | MIMIR confirms no corroborating evidence |
| 14 services go down | Impact gate flags $2M/hour blast radius |
| Incident response scrambles | System shifts to diagnostic mode |
| Post-mortem: "AI did it" | Investigation packet generated in seconds |
| Insurance claim denied (no audit trail) | Full ledger chain proves governance |

### Governance Principle

> No AI action executes without passing integrity, evidence, and impact validation.

### Value Proposition (What the buyer hears)

- Prevents autonomous system self-damage
- Creates deterministic audit trail (insurance-grade)
- Enables compliance with NIST Agent Initiative + GSAR 552.239-7001
- Provides defensible decision records for legal and insurance
- Turns "AI went rogue" into "AI was governed"

### Why This Demo Works

Once someone sees an AI agent about to nuke a production database — and KORUM stops it with a scored, auditable, challengeable BLOCK — they can't unsee the risk of NOT having it. Every autonomous system they deploy after that moment feels naked without governance.

---

## What Exists vs What Needs Building

| Component | Status | Location |
|---|---|---|
| Role conflict (Red Team vs Council) | **Shipped** | engine_v2.py — Red Team override |
| Diagnostic gate | **Shipped** | engine_v2.py — `_requires_diagnostic_first()` |
| Governor scoring + floors | **Shipped** | engine_v2.py — `_calibrate_packet_confidence()` |
| LOKI block → forces diagnostic-first | **Shipped** | engine_v2.py — `_red_team_premature_action` |
| Evidence classification | **Shipped** | exporters.py — Input Data / Derived / Analytical |
| Decision Ledger (hash chain) | **Shipped** | ledger.py |
| Falcon Protocol (PII redaction) | **Shipped** | falcon.py |
| Investigation Focus label | **Shipped** | engine_v2.py — replaces "Mitigation" |
| Tier 3: Impact Escalation gate | **Not built** | Needs: `_assess_impact_severity()` in engine_v2.py |
| HUMAN_REVIEW decision status | **Not built** | Needs: new VIE status + UI for human approval flow |
| Role Registry config file | **Not built** | Needs: role_registry.json or .yaml |
| DNA config files (per vertical) | **Not built** | Needs: dna_profiles/ directory |
| Vertical ontology schemas | **Not built** | Needs: verticals/ directory |
| Evidence Graph (entity extraction) | **Not built** | Needs: NER + relationship parsing |
| Evidence Graph (visualization) | **Not built** | Needs: D3.js or similar |
| LOKI anomaly scoring | **Not built** | Needs: pattern matching on graph edges |
| VIE forensic template | **Not built** | Needs: export template in exporters.py |
| Vertical adapters (Splunk, SNMP) | **Not built** | Needs: data ingestion layer |

---

*Specification document. See also: ARCHITECTURE_VISION.md, VERTICAL_STRATEGY.md, FUTURE_IDEAS.md*
