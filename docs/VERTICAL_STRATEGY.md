# KORUM OS — Vertical Strategy & Domain Specialization

### Living Document — March 2026
### Status: Ideation / Architecture Planning

---

## Positioning Statement

> "Korum doesn't make decisions. It tells you how much you should trust the decision being made."

## What KORUM Is Selling

Not dashboards. Not AI answers. **Decision Liability Protection.**

## Core Thesis

KORUM OS is a **platform**, not a point solution. The engine (Council, Governor, Falcon, Ledger) is domain-agnostic. Verticals are **configurations** — DNA profiles, Falcon rules, personas, Governor thresholds, and UI theming — not separate products.

**Option C Model (Selected):** One product. Customer picks their domain at setup. DNA config shapes everything. Same codebase, same deployment.

### Vertical Selection Criteria (All 3 Must Apply)
1. **High consequence decisions** — wrong answer has real cost
2. **Multiple conflicting data sources** — no single truth
3. **Accountability pressure** — someone has to explain why

```
KORUM OS (Core Engine)
│
├── Falcon Protocol ─── PII/data protection (rules vary by domain)
├── Confidence Governor ── authority resolution (thresholds vary by domain)
├── Decision Ledger ───── audit trail (universal)
├── Council Engine ────── multi-model adversarial (personas vary by domain)
│
├── KORUM DEFENSE ──── Drone telemetry, C-UAS, ISR, force protection
├── KORUM CYBER ────── Zero Trust, threat intel, incident response, forensics
├── KORUM TELECOM ──── Network ops, CPNI compliance, outage analysis
├── KORUM FINANCE ──── Risk assessment, audit, regulatory compliance
├── KORUM LEGAL ────── Contract review, regulatory exposure, compliance
└── KORUM [NEXT] ───── Future verticals
```

### What Changes Per Vertical
- Workflow DNA (personas, tone, risk bias, output structure)
- Falcon rules (what gets redacted — CPNI, ITAR, PHI, PII)
- Evidence classification context (sensor telemetry vs financial statements)
- Governor thresholds (defense = 80+ to recommend, creative = 60+)
- UI theming (colors, terminology, report templates)

### What Stays Universal
- The engine
- The adversarial council
- The Governor's authority
- The Ledger
- Falcon architecture
- Export pipeline
- Report standard (VIE)

---

## CYBER VERTICAL — Deep Dive

### The Tactical Fork

In 2026, "General Cyber AI" is noisy and crowded. KORUM must choose a posture:

### Posture A: The Forensic Hunter (Post-Mortem Specialist)

**Mission:** Turn 280 days of dwell time into 280 seconds of analysis.

**Why this fits KORUM:** The Audit Trail Ledger and VIE are built for *integrity*. In 2026, the biggest pain point for CISOs isn't predicting threats (1,000 tools do that) — it's **liability and reporting** after a breach or when an agentic AI goes rogue. KORUM's "Forensic Trace" is the unique selling point.

**Workflow:**
1. **Ingestion** — Pull in raw logs and telemetry
2. **Falcon Pass** — Ghost View redacts sensitive employee names/IPs so the Council analyzes attack patterns without data spillage
3. **Council Loop** — Lead analyst coordinates "Who/What/When" while adversarial role plays the intruder to test if evidence holds
4. **Red Team** — Challenges the reconstruction, finds gaps in the forensic chain
5. **Output** — A VIE that serves as a **legal-grade incident report**, ready for board of directors or regulatory filing

**Key Differentiator:** Nobody else produces a hash-chained, tamper-evident forensic reconstruction where every AI conclusion is cross-verified and auditable. This isn't a summary — it's evidence.

### Posture B: The Predictive Sentinel (Pre-Incident Specialist)

**Mission:** Identify weak signals and attack paths before exploitation.

**Workflow:**
1. **Simulation** — Red Team permanently ON. Council generates "What If" scenarios based on latest zero-day trends
2. **Exposure Mapping** — Falcon Rules map where high-value data ("Crown Jewels") is most vulnerable
3. **Output** — A VIE as a **weekly Battle Plan** telling SOC exactly which ports to close or identities to rotate

**Key Differentiator:** Continuous adversarial simulation, not reactive alerting.

### Recommendation: Lead with Forensic Hunter

**Rationale:**
- Ledger + VIE = built for integrity and legal-grade output
- Less crowded than predictive/threat intel (Crowdstrike, SentinelOne own that)
- CISOs need *defensible reports* more than more alerts
- Natural expansion: Forensic Hunter → add Predictive Sentinel later as second workflow
- Falcon Protocol is the perfect fit — redact before analysis, prove you never exposed raw data during investigation

### Cyber DNA Profile (Draft)

```
KORUM CYBER — FORENSIC HUNTER:
  Posture: Forensic Investigator
  Goal: Reconstruct attack chain with legal-grade precision
  Tone: Clinical, evidence-first, zero speculation
  Risk Bias: Conservative (no conclusions without verified evidence)
  Time Horizon: Post-incident reconstruction
  Governor Floor: 75 (forensic conclusions require high confidence)
  Falcon Rules: Employee PII, internal IPs, system names, credentials
  Output: Incident VIE — board-ready, regulator-ready
  Red Team: Always ON (challenge the reconstruction)
```

---

## VERTICAL #1: TELECOM NETWORK OPERATIONS (Home Field)

**Priority: HIGHEST — Unfair Advantage Vertical**

### Where KORUM Fits
- NOC decision validation layer
- Outage root-cause verification
- Capex vs optimization decisions

### The Problem Today
- Engineers guess root cause under pressure
- Vendors push hardware upgrades as default solution
- No unified "truth scoring" across conflicting data sources

### KORUM Play
**Ingest:** SNMP / telemetry, ticketing (ServiceNow), field reports

**Output:** Decision Integrity Packet

**Example:**
```
"Upgrade routers" → Score: 41 / LOW CONFIDENCE
  Governor: vendor recommendation without baseline diagnostics

"Traffic engineering fix" → Score: 72 / HIGH CONFIDENCE
  Governor: supported by telemetry data, lower cost, reversible
```

### Monetization
- Per NOC deployment
- Per-node or per-region licensing

### Moat
Carlos understands fiber realities, dispatch inefficiencies, false outages. This is domain expertise that can't be hired — it's lived.

### DNA Profile
```
KORUM TELECOM:
  Posture: Operations Analyst
  Goal: Root-cause verification before capex commitment
  Tone: Direct, operational, evidence-first
  Risk Bias: Conservative (no upgrades without diagnostics)
  Governor Floor: 70
  Falcon Rules: CPNI, subscriber data, internal network topology
  Output: Decision Integrity Packet — NOC-ready
  Red Team: On request (challenge vendor recommendations)
```

---

## VERTICAL #2: FINANCIAL DECISION INTELLIGENCE

### Where KORUM Fits
- Portfolio decision validation
- Risk analysis layer
- "AI vs human bias detector"

### The Problem Today
- AI gives confident but wrong answers
- Analysts cherry-pick data to support conclusions
- No audit trail of reasoning behind recommendations

### KORUM Play
**Council roles:** CFO, Risk Officer, Bear Analyst (Red Team)

**Output:** Decision packet with contradictions, missing data, false assumptions exposed

**Example:**
```
"Buy NVDA"
  → Red Team: "Overvaluation risk ignored, concentration risk"
  → Missing: downside scenario analysis
  → Final Score: 58 (NOT INVESTMENT GRADE)
```

### Monetization
- Hedge funds (premium tier)
- Wealth advisors (per-seat)
- Retail premium tier (later expansion)

### DNA Profile
```
KORUM FINANCE:
  Posture: CFO / Auditor
  Goal: Downside protection, bias detection
  Tone: Analytical, precise, detached
  Risk Bias: Downside-aware
  Governor Floor: 85 (highest bar — financial recommendations)
  Falcon Rules: Account numbers, SSNs, financial PII, insider information
  Output: Audit-ready brief, regulatory filing support
  Red Team: Always ON (Bear Analyst challenges every thesis)
  Evidence: Strict — no derived metrics without showing math
```

---

## VERTICAL #3: CYBERSECURITY / SOC (Mini-SOC Vision)

### Where KORUM Fits
- Alert validation layer
- False positive killer
- Incident decision engine

### The Problem Today
- Alert fatigue (90% noise)
- Junior analysts escalate garbage
- AI tools hallucinate threats

### KORUM Play
**Ingest:** Splunk / Sentinel / ELK alerts

**Evaluate:** "Is this actually a threat?"

**Example:**
```
"CRITICAL ALERT" → downgraded to
  Score: 33 → insufficient evidence, false positive pattern

"Low alert" → escalated to
  Score: 81 → high-risk anomaly, matches known TTP
```

### Monetization
- MSSPs (Managed Security Service Providers)
- Enterprise SOCs

### Strategic Insight
This is where KORUM becomes **"AI that audits AI security tools."** That positioning is massive — every SOC runs AI tools that generate alerts, but nobody audits whether those alerts are real.

### DNA Profile
See Forensic Hunter DNA in ROLE_REGISTRY_SPEC.md for the post-incident posture. SOC alert validation would use a lighter "Sentinel" DNA with lower thresholds for triage speed.

---

## VERTICAL #4: HEALTHCARE DECISION VALIDATION (High Value / High Barrier)

### Where KORUM Fits
- Clinical decision validation
- Treatment recommendation sanity check
- **NOT diagnosing** — confidence validation layer

### The Problem Today
- AI recommendations are untrusted by clinicians
- Doctors are liable for wrong decisions
- Patient data is fragmented across systems

### KORUM Play
KORUM does NOT diagnose. Instead:

**Input:** "Treatment A recommended"

**Output:**
```
→ Missing labs identified
→ Conflicting evidence flagged
→ Confidence score: 62 / CONDITIONAL
→ Investigation Focus: order CBC and metabolic panel before proceeding
```

### Monetization
- Hospitals
- Insurance companies

### Note
Long-term play — regulatory heavy (HIPAA, FDA). But the Falcon Protocol is purpose-built for PHI redaction, which gives KORUM a head start others don't have.

### DNA Profile
```
KORUM HEALTH:
  Posture: Clinical Validator
  Goal: Confidence validation, NOT diagnosis
  Tone: Clinical, cautious, evidence-only
  Risk Bias: Extremely conservative
  Governor Floor: 90 (highest — patient safety)
  Falcon Rules: PHI, patient identifiers, provider names, facility data
  Output: Clinical Confidence Assessment
  Red Team: Always ON
  Diagnostic-first: ALWAYS (never recommend action without full evidence)
```

---

## VERTICAL #5: GOVERNMENT / COMPLIANCE / AUDIT

### Where KORUM Fits
- Audit defense system
- Decision traceability engine
- AI explainability layer

### The Problem Today
- No explainability in AI decisions
- Compliance risk skyrocketing as AI adoption grows
- "Who approved this?" chaos in regulated environments

### KORUM Play
Every decision becomes:
- **Traceable** — Ledger chain shows exactly how
- **Scored** — Governor quantifies confidence
- **Challengeable** — Red Team stress-tests before action

**Output:** Audit Packet + Evidence Trail

### Monetization
- Government contractors
- Regulated industries (banking, energy, pharma)

### DNA Profile
```
KORUM GOV:
  Posture: Compliance Auditor
  Goal: Decision traceability, regulatory defensibility
  Tone: Formal, precise, citation-heavy
  Risk Bias: Conservative
  Governor Floor: 80
  Falcon Rules: Classified markings, personnel data, contract numbers
  Output: Audit Defense Packet
  Red Team: Always ON
  Ledger: Full event chain required for every output
```

---

## VERTICAL ADAPTER ARCHITECTURE

One core engine. Different inputs. Same governance.

| Layer | Example |
|-------|---------|
| Telecom Adapter | SNMP, NOC telemetry, ServiceNow tickets |
| Finance Adapter | Market APIs, statements, regulatory filings |
| SOC Adapter | Splunk / Sentinel / ELK alerts |
| Healthcare Adapter | EHR data (FHIR), lab results, imaging reports |
| Compliance Adapter | Document ingestion, regulatory databases |
| Defense Adapter | ISR feeds, SIGINT, sensor telemetry |

---

## ENTERPRISE TARGETS

| Vertical | Target | Pain Point | KORUM Advantage |
|----------|--------|-----------|-----------------|
| Telecom | Verizon, carriers | Root-cause guessing, vendor pressure, CPNI | Home field + Falcon CPNI + Decision Integrity Packet |
| Cyber | QanAPI, MSSPs | Post-breach forensics, alert fatigue, false positives | Forensic VIE + Falcon redaction + "AI auditing AI" |
| Finance | Hedge funds, wealth advisors | Cherry-picked data, no audit trail | Bear Analyst Red Team + Governor bias detection |
| Healthcare | Hospitals, insurers | Untrusted AI, liability, fragmented data | Falcon PHI + confidence validation (not diagnosis) |
| Gov/Compliance | Contractors, regulated industries | AI explainability, audit chaos | Full Ledger chain + Audit Defense Packet |
| Defense | DOD/SBIR | Multi-source intelligence, classification | Council + Ledger + air-gapped fallback |

---

## UI THEMING (Per Vertical)

| Vertical | Primary | Accent | Terminology | Report Style |
|----------|---------|--------|-------------|-------------|
| Cyber | Dark charcoal | Threat red | Incident, breach, IOC, TTP | Forensic report |
| Defense | Dark green | Amber gold | SITREP, OPORD, ISR, C-UAS | Tactical brief |
| Telecom | Navy | Cyan | NOC, outage, capacity, CPNI | Operations assessment |
| Finance | Dark navy | Green | Audit, exposure, compliance, variance | Regulatory brief |
| Legal | Charcoal | Gold | Filing, exposure, precedent, liability | Legal memo |

---

*This document captures strategic direction and is updated as ideas mature. Engine architecture decisions live in MEMORY.md and KORUM_DNA.md.*
