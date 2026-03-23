# KorumOS 4-Layer System Architecture

KorumOS is built on a "Trust-Through-Structure" philosophy. Every decision must be traceable, auditable, and secure. The system is divided into four distinct operational layers that manage the lifecycle of a high-stakes decision.

## 1. The HUD Layer (Command Interface)
The **Heads-Up Display (HUD)** is the primary operational environment where users command the Council.
*   **Mission Commander**: The primary dashboard for launching research, tech, and genealogy missions.
*   **Mission Log**: Real-time streaming of council discussion phases.
*   **Artifact Dock**: Persistent storage and export of finalized **Decision Packets**.
*   **Falcon Preview**: The "Ghost Map" interface that allows users to review redactions before they leave the firewall.

## 2. The Falcon Layer (Security & Redaction)
The **Falcon Protocol** acts as a secure air-gap between the user's sensitive data and external Large Language Models (LLMs).
*   **Zero-Exposure Gateway**: Redacts PII/PHI using a 3-pass identification engine (Regex, Heuristic NER, Custom Dictionary).
*   **Mission Vault**: Deterministically pseudonymizes entities (e.g., PERSON_01) to maintain AI reasoning while protecting identity.
*   **Data Minimization**: Strips 80%+ of metadata while preserving the semantic "Signals" needed for the Council to make high-quality calls.

## 3. The Council Layer (Intelligence Engine)
The **Council Engine** is the "Think Tank" where multiple AI agents collaborate to forge a decision.
*   **Sequential Assembly**: Moves from **Persona Expansion** -> **Council Discussion** -> **Red Team Attack** -> **Validated Intelligence Estimate (VIE)**.
*   **Workflow DNA**: 18 specialized archetypes (Genealogy Archivist, CFO, Legal Auditor, etc.) that dictate the engine's posture and output structure.
*   **Confidence Governor**: Enforces strict scoring rules (Dual-Confidence Model) and prevents overconfidence through the **Assumption Firewall** and **Source Concentration** audits.

## 4. The Ledger Layer (Audit & Provenance)
The **Audit Trail Ledger (ATL)** is the system's "Black Box" recorder.
*   **Tamper-Evident Chain**: Every event in the Council is hashed and chained, creating an immutable history of how a decision was reached.
*   **Evidence Archive**: A "Thick Vault" (locked behind compliance roles) that stores the raw, unredacted payloads mapped to their ledger entries via SHA-256 hashes.
*   **Decision Provenance**: Allows an auditor to reconstruct the exact discussion that led to any specific line in a final report, providing **Forensic Truth** for every executive call.

---
*Produced by Korum-OS Decision Intelligence / Systems Overview v2.2*
