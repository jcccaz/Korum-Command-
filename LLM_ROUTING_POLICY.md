# LLM Routing Policy

## Coding Session Routing (Korum Backend)

*In prose for the team:*

Use **Gemini 2.5 Fast** for exploratory work, boilerplate, and local edits: new handlers, CRUD endpoints, simple adapters, log formatting, and “explain this file/module” queries.

Use **Claude** for cross‑cutting or risky changes: changes that span multiple services, modify Aegis Ledger schemas, FalconProtocol paths, security/crypto, or error‑handling around PII and audit events.

Use **Chat/GPT** as a middle tier: tests, small refactors, and type/interface cleanups that don’t directly touch security or ledger semantics.

### Orchestrator Implementation Policy

A simple policy you can implement in the orchestrator:

- If the prompt mentions: `aegis_ledger`, `FalconProtocol`, `decision_contested_by_redteam`, `auth`, `crypto`, or “refactor across services” → **route to Claude**.
- If the prompt is about a single file or function, or “generate new route/controller/DTO” → **route to Gemini Fast**.
- If the prompt is “write tests for X”, “tighten types”, or “clean this module” → **route to Chat/GPT**.

### Example Coding Routing Table

| Task type | Default model | Notes |
| :--- | :--- | :--- |
| New CRUD endpoint / simple handler | Gemini 2.5 Fast | Fast, cheap, local edits only |
| Explain this module / summarize file | Gemini 2.5 Fast | No cross‑service changes |
| Unit/integration test generation | Chat / GPT | Good balance of quality vs cost |
| Type/interface cleanup (TS, schemas) | Chat / GPT | Medium‑risk refactors |
| Aegis Ledger schema changes | Claude | High‑risk, must be correct |
| FalconProtocol / PII handling code | Claude | Privacy & compliance sensitive |
| Cross‑service refactor / orchestrator | Claude | Needs deep context |
| Large boilerplate (docs, comments) | Gemini 2.5 Fast | Let it burn tokens cheaply |

---

## Telecom Decision Dossier Routing

*Text for the design doc:*

**Stage 1 – Draft dossier (Gemini Fast):** Build the first‑pass telecom narrative (slow speeds, infra constraints, risks, tradeoffs, basic KPIs) with Gemini 2.5 Fast.

**Stage 2 – Red‑team + reconciliation (Claude):** Feed a compact structured summary (key risks, assumptions, KPIs, proposed decision) into Claude as the red‑team and reconciliation step. Claude’s job is to attack assumptions (e.g., diagnostic‑first churn risk), assign severity, and update decision status and confidence before Aegis Ledger writes the event.

**Stage 3 – Lightweight commentary (Chat/GPT):** If we need user‑friendly executive summaries or email‑style explanations from the finalized dossier, use Chat/GPT for that layer.

### Example Dossier Pipeline

1. **Gemini Fast** generates the full telecom dossier: executive summary, tradeoff table, risks, initial decision + confidence.
2. **Korum** compresses that into a JSON summary (risks, assumptions, KPIs, decision, confidence) and sends it to Claude with the red‑team prompt.
3. **Claude** returns: severity, `exploit_class`, `attack_path`, and recommended defensive actions, plus any proposed adjustment to decision/confidence.
4. **Korum** reconciles base + red‑team, sets status (FINAL / CONTESTED / ESCALATED), and emits the Aegis Ledger `decision_contested_by_redteam` event.
5. *Optionally*, **Chat/GPT** turns that into a short exec email or Jira ticket summary.

*This keeps most tokens on Gemini, uses Claude only where its extra reasoning cost is justified, and lets Chat/GPT sit in the middle for tests and comms.*
