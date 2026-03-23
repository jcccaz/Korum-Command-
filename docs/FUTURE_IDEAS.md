# KORUM OS — Future Ideas & Roadmap

### Living Document — March 2026
### Status: Ideation + Planned Phases

---

## PLANNED PHASES (Architecture Defined, Not Yet Built)

### Phase 2: Falcon Deterministic Pseudonymization
- PERSON_01 / ORG_01 style placeholders (currently SHA-256 hashed)
- Mission-scoped MissionVault — same entity gets same pseudonym across an entire mission
- Enables cross-session analysis without re-exposing PII
- Ghost Preview UI polish: trust statement, "VISIBLE TO AI MODELS" label, redaction legend
- Falcon mode selector: Assist / Enforce / Strict

### Phase 3: Mission HUD + Ledger Stream UI
- Operator situational awareness dashboard
- Real-time Ledger event stream (like a security camera feed for AI decisions)
- Privacy status indicators (Falcon active/inactive, what's redacted)
- Mission timeline visualization
- Decision chain replay (see how the council reached its conclusion)

### Phase 4: Decision Replay ("Time Travel")
- Reconstruct any past decision from Ledger events
- Three replay modes:
  - **Integrity mode** — verify the chain hasn't been tampered with
  - **Policy mode** — re-run with updated governance rules to see if outcome changes
  - **Model upgrade mode** — replay with newer models to compare reasoning quality
- "What would the Governor have said 6 months ago?" capability

### Enterprise Hardening
- **Sentinel** — prompt injection defense layer (detect and block adversarial prompts)
- **API-first / headless mode** — KORUM as a service, no UI required
- **Goldfish retention** — configurable data TTL, auto-purge after N days
- **MFA/TOTP** — infrastructure ready (pyotp installed), needs UI activation
- **SSO integration** — SAML/OIDC for enterprise identity providers

---

## VERTICAL SPECIALIZATION (See VERTICAL_STRATEGY.md)

### Domain Configurations (Option C Model)
- One product, domain selected at setup
- DNA configs, Falcon rules, personas, Governor thresholds per vertical
- UI theming per domain (colors, terminology, report style)
- Verticals: Defense, Cyber, Telecom, Finance, Legal, and future domains

### KORUM CYBER — Forensic Hunter (Priority Vertical)
- Post-breach forensic reconstruction
- Legal-grade incident VIE (board-ready, regulator-ready)
- 280 days of dwell time → 280 seconds of analysis
- Falcon redacts employee PII/IPs during investigation
- Red Team always ON to challenge forensic conclusions
- See VERTICAL_STRATEGY.md for full DNA profile

### KORUM DEFENSE — Drone & C-UAS Intelligence
- Drone telemetry analysis
- Counter-UAS threat assessment
- ISR data fusion from multiple sensor sources
- SITREP-style output format
- Air-gapped operation for classified environments

---

## AUTO-CHART GENERATION (Next Up — Code Ready)

### Current State
- Charts render on-screen via Chart.js / SVG (chart_engine.py)
- Manual flow: Visualize button → Dock → Export picks them up
- Charts appear in Word/PDF exports (side-by-side with prose)

### Planned Enhancement
- During synthesis, detect chartable data (tables, metrics, percentages)
- Auto-generate charts via chart_engine.py without manual clicks
- Embed as docked artifacts in the intelligence object
- Charts ride into export automatically via existing artifact pipeline
- Manual Visualize + Dock option preserved for custom charts
- Chart types: bar, donut (user preference), line, comparison

---

## DNA SHARPENING PASS (Output Quality)

### Goal
Every workflow tab's Phase 4 (synthesis) delivers a polished, actionable artifact — not glued-together analysis.

### Reference Model
SOCIAL_POST pipeline: phases build sequentially, final output is copy-paste ready.

### Apply Same Pattern To:
- **WAR_ROOM** → executable action plan (not a summary of what was discussed)
- **FINANCE** → decision-ready brief (audit-grade, shows math)
- **CREATIVE** → finished deliverables (not brainstorming notes)
- **LEGAL** → ready memo (cite-ready, regulatory-mapped)
- **DEFENSE** → tactical SITREP (actionable, time-bucketed)
- **CYBER** → incident report or threat assessment (evidence-mapped)

### Output Structure Alignment
Each workflow's `output_structure` in WORKFLOW_DNA should match what the final phase actually produces. No mismatch between schema and reality.

---

## UI / UX IDEAS

### Domain Onboarding
- First-time setup: "What's your domain?" picker
- Loads appropriate DNA, Falcon rules, personas, theme
- Can switch domains without losing data

### Report Visual Diversity
- Side-by-side charts with prose (shipped)
- Donut charts for KPI visualization
- Pull quotes for key findings (inline, not boxed)
- Color-coded risk heat maps
- Timeline visualizations for action priorities

### Intelligence Feed (Shipped)
- Unified popup for follow-ups, verifications, interrogations
- Card-based viewer with type badges (amber/orange/red)
- Each card has its own DOCK button
- Resets per mission

### Settings Panel (Shipped)
- Language mirroring toggle
- Score delta pills toggle
- Provider preferences
- Theme selection (future: per-domain themes)

---

## DOCUMENTATION GAPS

### Exists
- White Paper v1.0 (needs v2.0 update — see KorumOS_White_Paper.md)
- Onboarding Manual
- Demo Packet
- Strategic Brief
- System Spec Record
- Trade Secret Controls
- Coding Agent Protocol

### Needs Creation
- **GOVERNOR.md** — Confidence Governor documentation (how scoring works, dual-confidence model, score bands, diagnostic-first logic)
- **FALCON.md** — Falcon Protocol documentation (3-pass redaction, Ghost Preview, Quick Protect, placeholder maps)
- **LEDGER.md** — Decision Ledger documentation (hash chaining, event types, verification API)
- **WORKFLOW_DNA.md** — Complete workflow DNA reference (all 18 workflows, personas, output structures)
- **API_REFERENCE.md** — All endpoints, request/response shapes
- **EXPORT_GUIDE.md** — Export formats, what each includes, customization

### White Paper v2.0 Update Needed
- Add Falcon Protocol (not in v1.0)
- Add Decision Ledger (not in v1.0)
- Add Confidence Governor (not in v1.0)
- Add Evidence Classification system
- Add Red Team dominance rule
- Add diagnostic-first posture
- Reframe from "multi-AI platform" to "Adversarial Decision Governance System"
- Lead with governance, not provider list

---

## BUSINESS / GO-TO-MARKET IDEAS

### Enterprise Targets
| Target | Vertical | Entry Point |
|--------|----------|-------------|
| QanAPI | Cyber | Zero Trust validation, forensic reporting |
| Verizon | Telecom | CPNI compliance, operational intelligence |
| DOD/SBIR | Defense | Multi-source intelligence, audit trail |

### Positioning
- **Tagline:** "Making every AI decision defensible"
- **Category:** Decision Intelligence / AI Governance
- **Not competing with:** ChatGPT, Copilot (assistants), AutoGen, LangGraph (frameworks)
- **Competing with:** Palantir AIP (decision intelligence), but with adversarial governance they don't have

### Differentiators vs Market
| Their Trend | KORUM's Answer |
|---|---|
| Governance-as-Code (Microsoft) | Confidence Governor + Decision Ledger |
| Grounding (Google Vertex) | Truth Scoring + Evidence Classification |
| Observability (AgentRx) | Ledger chain + Provenance table |
| Role-Based agents (CrewAI) | 60+ personas + Workflow DNA |
| Zero-Copy (industry) | Falcon Protocol — models never see raw PII |

### Key Insight
The providers are interchangeable. The governance layer is what no one else has. Lead with Falcon, Ledger, and Governor — not the model list.

---

## WILD IDEAS (Unvalidated, Worth Exploring)

- **KORUM Marketplace** — community-contributed DNA configs, personas, Falcon rule packs
- **Multi-tenant SaaS** — org-level isolation with shared infrastructure
- **Decision Diffs** — compare two VIEs side-by-side (e.g., before/after a policy change)
- **Continuous Monitoring** — scheduled recurring missions (daily cyber posture check, weekly finance review)
- **Natural Language Falcon Rules** — "redact anything that looks like a social security number" → auto-generates regex
- **VIE Confidence Trends** — track how confidence scores change over time for the same topic
- **Mobile Command** — stripped-down mobile interface for field operators (defense use case)
- **Voice Input** — speak a mission brief, KORUM processes it (field conditions)
- **Regulatory Auto-Map** — detect which regulations apply based on content (HIPAA, ITAR, CPNI, SOX)

---

*This document captures ideas at various stages of maturity. Not all will be built. Engine architecture decisions live in MEMORY.md and KORUM_DNA.md. Vertical strategy lives in VERTICAL_STRATEGY.md.*
