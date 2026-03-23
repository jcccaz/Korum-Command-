# KorumOS Workflow DNA Specification

The **Workflow DNA** registry is the elite logic layer of KorumOS. It defines the "personality," goals, and structural constraints for every mission. When a mission is launched, the engine injects the corresponding DNA into the Council's prompt, forcing the AI to adopt a specific professional posture.

## 1. Core Workflow Manifest

KorumOS currently supports 18 specialized workflows and several aliases.

| Workflow ID | Posture (Role) | Primary Goal | Output Structure |
| :--- | :--- | :--- | :--- |
| **WAR_ROOM** | Tactical Commander | Immediate crisis containment (0-72h). | Situation, Threat, Immediate Action, Resource Allocation. |
| **RESEARCH** | Strategic Researcher | Fact-dense baseline with implications. | Summary, Key Signals, Evidence, Scenarios, Confidence. |
| **GENEALOGY**| Lead Investigator | Forensic lineage reconstruction. | Lineage, Archival Table, Migration, Discrepancies. |
| **FINANCE**  | CFO / Auditor | Economic viability & downside protection. | Cost, Revenue, Sensitivity Table, ROI Summary. |
| **LEGAL**    | General Counsel | Exposure reduction & compliance. | Regulatory Exposure, Risk Mitigation, Posture. |
| **CYBER**    | Red Team Lead | Active threat identification & defense. | Threat Intel, Attack Surface, Mitigation Playbook. |
| **DEFENSE**  | Intel Analyst | Geopolitical awareness & OPSEC. | Situation, Force Disposition, COAs, Intel Gaps. |
| **STARTUP**  | VC Partner | Business viability & runway. | Market Opp, Unit Economics, GTM Strategy, Runway. |
| **AUDIT**    | Lead Auditor | Control failures & compliance gaps. | Scope, Control Findings, Gap Analysis, Remediation. |
| **MEDICAL**  | Chief Medical Officer | Evidence-based clinical safety. | Clinical Assessment, Differential, Risk-Benefit. |
| **CREATIVE** | Creative Director | Bold concepts & tactical drafting. | Concept, Audience, Draft Deliverable, Execution. |
| **SCIENCE**  | Principal Investigator| Methodological rigor & reproducibility. | Hypothesis, Data Analysis, Limitations, Conclusions. |
| **TECH**     | CTO / Architect | Architecture & scalability. | Tech Trade-offs, Scalability, Implementation Plan. |
| **INTEL**    | Senior Intel Analyst | Finished intel with source grading. | Key Judgments, analytic Confidence, Alt Hypotheses. |
| **SYSTEM**   | SRE Lead / Systems Eng| System status & root cause. | System Status, Root Cause Analysis, Resolution Steps. |
| **SOCIAL_POST**| Founder-Builder | Authority-driven technical narratives. | Target Audience, Core Hook, Main Draft, Engagement. |
| **EOM_STATEMENT**| CFO | Monthly financial reporting. | P&L, Balance Sheet, Cash Flow, Burn Rate, Runway. |
| **PORTFOLIO_BUILDER**| Hedge Fund PM | Actionable investment picks with numbers. | Macro Setup, Screened Candidates, Architecture, Final Portfolio. |

## 2. Dynamic Posture Switching

KorumOS uses **Query-Aware DNA Mapping** to automatically switch postures without user input.

### 2.1 The "Archivist" Auto-Detection
If the system detects keywords like *biography, genealogy, lineage, relative,* or *ancestor* within a RESEARCH query, it automatically injects a **Forensic Research Depth Block**.
*   **Hard Rule**: No generic summaries allowed. Every claim must anchor to a date, location, or source type.
*   **Outcome**: Effectively switches the engine from "General Research" mode into **"Forensic Investigator"** mode.

## 3. Workflow Constraints

Each DNA entry also dictates the "internal mood" of the council:
*   **Risk Bias**: Ranges from *Conservative (Do No Harm)* in MEDICAL to *Risk-Tolerant (Push Boundaries)* in CREATIVE.
*   **Time Horizon**: Ranges from *0-72 hours* in WAR_ROOM to *Multi-generational* in GENEALOGY.
*   **Tone**: Ensures the language matches the profession (e.g., "Accounting-standard aligned" for EOM_STATEMENT).

---
*Produced by Korum-OS Decision Intelligence / Internal DNA Registry v2.2*
