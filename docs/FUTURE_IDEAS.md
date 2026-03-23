# KORUM OS — Future Ideas & Roadmap

### Living Document — March 2026
### Status: Ideation + Planned Phases

---

## PLANNED PHASES (Architecture Defined, Not Yet Built)

### Phase 2: Falcon Deterministic Pseudonymization — PARTIALLY SHIPPED
- ~~PERSON_01 / ORG_01 style placeholders~~ — **SHIPPED** (Sovereign Tokenization)
- ~~Canary Tokens (active deception)~~ — **SHIPPED**
- ~~Impact Escalation Gate (Tier 3)~~ — **SHIPPED**
- Mission-scoped MissionVault — same entity gets same pseudonym across an entire mission (DB-backed, cross-request)
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

## PQC HARDENING ROADMAP (Post-Quantum Cryptography)

### Current State — What's Shipped
- **Quantum Drift Check** (engine_v2.py) — detects legacy crypto (AES, RSA, 3DES, RC4, MD5) without PQC wrappers in user data. Flags violations referencing FIPS 203/204/205/206 with specific algorithm recommendations.
- **PQC Algorithm Awareness** — engine knows ML-KEM (Kyber), ML-DSA (Dilithium), SLH-DSA (SPHINCS+), FALCON (FN-DSA). Quantum Security workflow forces council to name specific algorithms and key lengths.
- **SHA-256 Ledger Hashing** — quantum-resistant for integrity (128-bit post-quantum security via Grover's halving). Audit trail is already quantum-safe at the hash layer.
- **Cryptographer Persona** — dedicated council role with AES/RSA, PKI, PQC, TLS/SSL, key management expertise.

### Phase A: Ghost-to-Quantum Envelope
- Wrap Falcon Ghost Maps in ML-KEM (FIPS 203) encrypted envelope at rest
- Even if full database is exfiltrated, Ghost Maps stay dark — attacker can't map placeholders to real identities
- Key management: per-mission encryption keys, HSM integration for enterprise
- **Priority:** High for government/defense contracts where data-at-rest encryption is mandatory

### Phase B: Quantum-Signed Ledger (ML-DSA)
- Sign each Decision Ledger entry with ML-DSA (FIPS 204) digital signatures
- Upgrades from integrity (hash chain) to non-repudiation (cryptographic proof of authorship)
- **The boardroom pitch:** "In 2030, when quantum computers are everywhere, our 2026 logs will still be legally valid and untamperable"
- Signature size consideration: ML-DSA signatures are ~2,420 bytes each — Ledger storage grows, but decision events are low-volume (not per-token)
- **Priority:** High for insurance-grade audit trails and government compliance

### Phase C: FIPS 206 Canary Beacons
- Embed FALCON/FN-DSA (FIPS 206) compact signatures into canary files
- If attacker modifies even one bit to remove tracking, signature breaks → MIMIR detects mismatch instantly
- FALCON chosen for compactness: ~666 byte signatures fit in 1KB canary files
- Extends current prompt-level canary tokens to file-level signed beacons
- **Priority:** Medium — requires Attribution Beacon (Tracer) infrastructure first

### Phase D: Crypto-Agility (Hot-Swap)
- If any PQC algorithm (e.g., Kyber) is found to have a mathematical flaw, KORUM can hot-swap to alternative (e.g., SPHINCS+ / FIPS 205) without breaking the system
- Implementation: algorithm selection as config, not hardcoded. Ledger records which algorithm signed each entry.
- Dual-signing during transition periods (old + new algorithm on same entry)
- **Priority:** Low urgency now, but architecturally important — design for it even if not building yet

### Dependencies
- `liboqs-python` or `pqcrypto` bindings (cross-platform build complexity)
- Key management infrastructure (HSM for enterprise, file-based for dev)
- Performance benchmarking (ML-DSA signing latency per Ledger event)
- Threat model justification (quantum attacks on decision platforms are 2028+ timeline)

### What This Unlocks
| Capability | Business Value |
|---|---|
| Encrypted Ghost Maps | "Even a full breach can't unmask protected identities" |
| Signed Ledger | "Our 2026 decisions are legally valid in 2030" |
| Signed canary beacons | "Tamper-proof attribution — modify it and we know" |
| Crypto-agility | "No single point of mathematical failure" |

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
- **Attribution Beacon (Tracer)** — canary documents that phone home when opened on attacker's machine. Let the hacker "steal" a file that's actually a signed beacon — it reports location, MAC, ISP back to MIMIR ledger. Legal complexity: beaconing to your own infrastructure is defensible, forwarding to law enforcement needs framework. Extends existing Falcon canary token concept from prompt-level to file-level.
- **Sniper** — KORUM's active defense layer with 3 modes: Tar Pit (drain attacker compute), Response (quarantine/revoke/alert after LOKI block), Attribution (precision evidence packets for CISA, insurance, board). See FALCON_SECURITY_DOCTRINE.md for full spec. ODIN identifies the target, LOKI confirms it's not a decoy, MIMIR logs the evidence, Sniper takes the shot

---

*This document captures ideas at various stages of maturity. Not all will be built. Engine architecture decisions live in MEMORY.md and KORUM_DNA.md. Vertical strategy lives in VERTICAL_STRATEGY.md.*
