# KorumOS Intelligence Lifecycle: End-to-End Workflow

This document provides a conceptual and technical walkthrough of the KorumOS decision-making process, from the initial user intent to the final auditable intelligence artifact.

---

## Phase A: Intent & Minimization (The Firewall)

Every mission begins with a User Query. Before any intelligence is generated, the system must secure the operating environment.

1.  **Workflow DNA Injection**: Based on the query or user selection, a specialized **Workflow DNA** (e.g., *Genealogy, Cyber, or Finance*) is loaded. This dictates the council's "mood," risk bias, and output structure.
2.  **Falcon Protocol Scrubbing**: The raw query passes through the **Falcon Layer**. All PII/PHI (Names, Emails, SSNs, IPs) is replaced with deterministic pseudonyms (e.g., `[PERSON_01]`). 
    *   *Result*: The AI operates on semantic "signals" without ever seeing the raw sensitive data.
3.  **Prompt Enhancement**: The de-identified query is "sharpened" into an intelligence-grade prompt, adding specific domain requirements and forensic directives.

## Phase B: The Council Deliberation (Sequential Reasoning)

KorumOS does not ask one AI for an answer. It convenes a **Sequential Council**.

1.  **Step-by-Step Expansion**: 
    *   **Card 1 (Analyst)** produces the baseline.
    *   **Card 2 (Architect)** reads Card 1's work and builds the structure.
    *   **Card 3 (Critic/Red Team)** reads both and identifies flaws, blind spots, or cognitive biases.
    *   **Card 4/5** integrate and refine the final intelligence pool.
2.  **Adversarial Hardening**: If **Red Team Mode** is active, a dedicated pass "attacks" the internal logic of the council, forcing a higher standard of proof.

## Phase C: Synthesis & The Governor (Truth Resolution)

The raw council discussion is a "data lake." The **Intelligence Synthesis Engine** (v2) converts this into a **Decision Packet**.

1.  **Truth Scoring**: Each major claim is compared across all five providers. If they disagree, the claim is marked as `CONFLICTING`. If they agree, it's `VERIFIED`.
2.  **Confidence Governor**: The system runs a final "Diagnostic Pass."
    *   It checks for **Source Concentration Risk** (e.g., did 80% of information come from one AI?).
    *   It applies **Soft Penalties** for unknowns or conflicting claims.
    *   It sets **Hard Caps** on confidence (e.g., you cannot have "Recommended" status if major conflicts exist).
3.  **Schema Enforcement**: The output is mapped strictly to the **DECISION_PACKET.MD** schema. If it doesn't fit, the system forces a re-composition.

## Phase D: Output & Audit (The Proof)

The intelligence is delivered as a hardened **Intelligence Brief**.

1.  **Report Generation**: The **Exporter** clean-ups the text, removes AI "chatter," and applies high-contrast themes (e.g., *Carbon Steel*).
2.  **Audit Trail Ledger (ATL)**: Every single step—from the Falcon hash to the final confidence score—is recorded in the ATL. This creates a "Forensic Trace" that allows an auditor to prove *why* a decision was made.

---
*Produced by Korum-OS Decision Intelligence / Operational Flow v2.2*
