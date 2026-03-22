# Provenance & Audit Trace — Specification

## Purpose

Every KorumOS decision must be traceable to the **actual runtime participants** — which models ran, what roles they played, what they produced, and who scored the result. The provenance block makes this visible in every Decision Packet and export.

**Core Rule:** If a field can't be populated from runtime data, show `UNKNOWN` — never silently omit.

## Schema

`provenance` is the 13th required top-level key in the Decision Packet:

```json
"provenance": {
  "decision_id": "string (run_id UUID)",
  "ledger_decision_id": "string (same as decision_id)",
  "scoring_source": "RULE_ENGINE | MODEL | HYBRID",
  "synthesis_model": "string (actual model that ran synthesis)",
  "red_team_model": "string | null",
  "council": [
    {
      "role": "string (e.g. STRATEGIST)",
      "provider": "string (e.g. openai)",
      "model": "string (e.g. gpt-4o)",
      "response_hash": "string (SHA-256)"
    }
  ]
}
```

## Data Flow

### Where provenance is built

1. **`engine_v2.py` → `synthesize_results()`** — After council execution, the provenance block is assembled from the `results` dict:
   - `decision_id` / `ledger_decision_id` = `context.run_id`
   - `scoring_source` = `"RULE_ENGINE"` (Confidence Governor)
   - `synthesis_model` = actual model returned by synthesis call
   - `council[]` = per-provider: role, provider name, model name, SHA-256 response hash
   - `red_team_model` = `None` (populated later)

2. **`app.py` → Red Team Arbiter** — After Red Team runs, the actual RT model is injected:
   - `v2_response.synthesis.provenance.red_team_model` = `rt_res.get('model')`

3. **`engine_v2.py` → `adapt_decision_packet_to_legacy_shape()`** — Provenance is passed through to the legacy export dict. If missing, a fallback with all `"UNKNOWN"` fields is generated.

### Where provenance is rendered

4. **`exporters.py` → PDF (ExecutiveMemoExporter)** — "PROVENANCE & AUDIT TRACE" section:
   - Metadata block: Decision ID, Ledger Decision ID, Scoring Source, Synthesis Model, Red Team Model
   - Council table: Role | Provider | Model | Response Hash (truncated to 16 chars)

5. **`exporters.py` → Word (WordExporter)** — Same structure, rendered before the final assessment footer.

## Graceful Degradation

- Missing `provenance` block entirely → section is skipped (no crash)
- Missing individual fields → display `"UNKNOWN"`
- No Red Team → Red Team Model shows `"N/A"`
- Empty council array → metadata still renders, table is skipped

## Export Appearance

```
PROVENANCE & AUDIT TRACE
─────────────────────────
Decision ID:        a1b2c3d4-e5f6-7890-abcd-ef1234567890
Ledger Decision ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Scoring Source:     RULE_ENGINE
Synthesis Model:    gpt-4o
Red Team Model:     gemini-2.0-flash

┌──────────────┬──────────┬──────────────────┬───────────────────┐
│ Role         │ Provider │ Model            │ Response Hash     │
├──────────────┼──────────┼──────────────────┼───────────────────┤
│ STRATEGIST   │ OPENAI   │ gpt-4o           │ 3a7f2b9c1d4e...  │
│ ARCHITECT    │ ANTHROPIC│ claude-sonnet-4-5 │ 8b2e4f6a9c1d...  │
│ CRITIC       │ GOOGLE   │ gemini-2.0-flash  │ 5c1d7e3f8a2b...  │
│ SCOUT        │ PERPLEXITY│ sonar-pro        │ 2d6a8c4e1f3b...  │
│ TELECOM_ENG  │ SPECIALIST│ Specialist(Cloud)│ 9f4b2d7a3c5e...  │
└──────────────┴──────────┴──────────────────┴───────────────────┘
```

## Files

| File | What Changes |
|---|---|
| `DECISION_PACKET.MD` | Schema: provenance as 13th key, key count 12→13 |
| `engine_v2.py` | Build provenance in `synthesize_results()`, pass through in legacy adapter, fallback validation |
| `app.py` | Inject Red Team model into provenance after RT arbiter |
| `exporters.py` | Render "Provenance & Audit Trace" in PDF and Word exports |

## Ledger Event Types (8 total)

| # | Event Type | When |
|---|---|---|
| 1 | `prompt_received` | User submits query |
| 2 | `falcon_redaction` | Falcon Protocol processes prompt |
| 3 | `mission_created` | Thread/mission initialized |
| 4 | `model_reasoning` | Each council model responds |
| 5 | `council_synthesis` | Synthesis phase completes |
| 6 | `decision_outcome` | Final decision scored |
| 7 | `human_checkpoint` | Operator intervention |
| 8 | `decision_contested_by_redteam` | Red Team FAIL verdict |

## Future: Ledger Reconstruction (Phase 4+)

The provenance block includes `ledger_decision_id` — the key to reconstruct the full audit trail from the Decision Ledger. In Phase 4 (Decision Replay), the Mission HUD will use this ID to walk the hash chain and replay every event in sequence. The export provenance is the summary; the ledger is the full tape.
