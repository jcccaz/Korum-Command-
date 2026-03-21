# KORUM OS - DECISION PACKET

## PURPOSE

This document defines the exact programmatic object that the Korum-OS Engine must produce to count as Korum-grade output. 

It serves as the absolute **Readiness Gate** between cognitive reasoning (the Engine) and rendering (the Exporter/UI). 

## CORE RULE: PACKET COMPLETENESS

The decision packet is a strictly typed contract. If a mandated slot is missing from the JSON/Object payload, it is trapped by the Validator/Normalizer layer. Export and rendering are immediately blocked. 

The LLM output should **never** go straight to the exporter. It must traverse:
`Composer → Validator/Normalizer → Exporter`

## REQUIRED PACKET SCHEMA

Every Korum-OS Decision Packet MUST map exactly to the JSON shape below. Extra keys are banned.

```json
{
  "decision_headline": "string",
  "executive_summary": "string",
  "go_no_go_call": {
    "decision": "GO | NO-GO | CONDITIONAL GO",
    "rationale": "string"
  },
  "confidence": {
    "band": "HIGH | MEDIUM | LOW",
    "score": 0,
    "basis": "string"
  },
  "verified_claims": [
    {
      "claim": "string",
      "status": "VERIFIED | PARTIAL | FALSE | UNVERIFIED",
      "source_ref": "string"
    }
  ],
  "risk_vectors": [
    {
      "title": "string",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "impact_type": "Financial | Operational | Strategic | Reputational",
      "description": "string",
      "mitigation": "string"
    }
  ],
  "assumptions": ["string"],
  "unknowns": ["string"],
  "immediate_actions": [
    {
      "action": "string",
      "owner": "string",
      "timeline": "string"
    }
  ],
  "alternatives_rejected": [
    {
      "option": "string",
      "reason_rejected": "string"
    }
  ],
  "evidence_trace": [
    {
      "point": "string",
      "support": "string"
    }
  ],
  "export_metadata": {
    "report_type": "string",
    "workflow": "string",
    "generated_at": "ISO-8601 string",
    "schema_version": "1.0"
  }
}
```

## VALIDATOR ENFORCEMENT

The intermediate Validator/Normalizer layer must execute these checks before releasing the packet to downstream exporters:
1. Verify all 12 top-level keys exist.
2. Verify required nested keys exist.
3. Verify enums are valid (e.g., `go_no_go_call.decision`).
4. Verify arrays contain objects of the correct shape.
5. Reject extra legacy payload branches like `sections`.
6. Return a `HARD FAIL` if the packet is irreversibly invalid, or normalize if drift is purely formatting.
