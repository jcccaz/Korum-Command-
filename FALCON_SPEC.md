# KorumOS Falcon Protocol Specification

The **Falcon Protocol** is the secure data minimization layer of KorumOS. It is designed to strip sensitive entities (PII/PHI) from user queries and documents **BEFORE** they reach external AI providers. Falcon ensures that the Council Engine operates on "de-identified" intelligence to reduce organizational exposure.

## 1. The 3-Pass Redaction Architecture

Falcon uses a layered approach to identify and mask sensitive data without external dependencies (Pure Python stdlib).

| Pass | Method | Targets |
| :--- | :--- | :--- |
| **Pass A** | **Pattern-Based (Regex)** | Structured identifiers: Emails, Phones, SSNs, IP Addresses, IBANs, Credit Cards, Custom Asset Tags. |
| **Pass B** | **Heuristic NER** | Unstructured entities: Person names (titled/initials), Organizations (via corporate suffixes), Locations (Cities/States/Countries). |
| **Pass C** | **Custom Dictionary**| Org-specific protected terms: Project names (e.g., "Project Aurora"), internal hostnames, and specific customer names. |

## 2. Redaction Levels

Administrators can configure the intensity of Falcon for each mission.

*   **LIGHT**: Regex patterns only. Masks structured identifiers like emails and SSNs but preserves proper names for context.
*   **STANDARD**: Regex + Heuristic NER. Masks names, organizations, and locations. The default security posture.
*   **BLACK**: Maximum redaction. Includes dates (relative or absolute), hostnames, and strict proper noun detection. Preserves sentence structure to maintain AI reasoning capability while maximizing anonymity.

## 3. The Mission Vault (Deterministic Pseudonymization)

Falcon does not simply [REDACT] text with generic blocks. It uses a **Mission Vault** to provide context-aware pseudonyms.

### 3.1 SHA-256 Determinism
*   Every unique entity (e.g., "John Doe") discovered within a mission is assigned a deterministic token (e.g., `[PERSON_01]`).
*   The same entity discovered in a different file or a later follow-up query will **always** receive the same token within that mission's scope.
*   **Zero PII Storage**: The Vault stores only the **SHA-256 hash** of the entity and its assigned token. The original PII is never persisted.

## 4. The Ghost Preview & Audit Inventory

To support transparency without compromising security, Falcon generates a **Ghost Map**.

*   **Ghost Map**: A safe-to-serialize token inventory that tracks which placeholders were used, their entity type (PERSON, ORG, etc.), and their character offset.
*   **Ghost Preview**: Allows the user to see exactly *what* was redacted (e.g., "Redacted 12 names and 3 locations") before the query is sent to the Council.
*   **Audit Trace**: Every redaction is logged in the **Audit Trail Ledger (ATL)**, ensuring that any AI-generated decision can be mapped back to its redacted source by authorized personnel.

## 5. Domain-Aware Stopwords

Falcon prevents "over-redaction" by using a dynamic dictionary.
*   Words like "Project," "Operation," or "Plan" are excluded from person-name detection.
*   **Workflow DNA Integration**: Falcon automatically loads domain-specific stopwords based on the mission type (e.g., loading "Statute" and "Plaintiff" for **LEGAL** workflows to prevent them from being flagged as proper names).

---
*Produced by Korum-OS Decision Intelligence / Internal Secure Layers v2.3*

## 6. Canary Tokens (Active Deception)

Falcon includes an active deception layer to detect model hallucinations and "jailbreak" attempts via **Canary Tokens**.

### 6.1 Injection Strategy
*   When Falcon redacts text, it generates 3-5 **Canary Tokens** (e.g., `[PERSON_3X1A2]`).
*   These tokens are procedurally generated and look like real redacted entities but have **no original value** in the Mission Vault.
*   They are appended to the redacted prompt sent to the Council: `\n[Additional referenced entities: [PERSON_3X1A2] [ORG_9K4B1]]`.

### 6.2 The Integrity Audit
*   Since Canary Tokens have no source in the original text, any model that references them in its response is definitively **hallucinating** or attempting to bridge "ghost" context.
*   **Integrity Violation**: If a canary is detected in the response, the Governor automatically triggers an **Integrity Failure** event in the Decision Ledger.
*   **Provable Hallucination**: This provides a binary, mathematical proof of reasoning failure, which is impossible with standard LLM evaluation methods.

---
*KorumOS Technical Standard / SEC-L3-ALPHA*
