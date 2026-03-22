# KORUM ATL — Consolidated Guidance for Engineering

## 1. High-level Architecture
Korum OS uses a **dual-layer audit model** to balance compliance metadata with data privacy.

### A. Witness Layer (Thin Ledger)
*   **Storage**: Append-only database table (`decision_ledger`).
*   **Content**: Metadata only. **No raw prompt/response text.**
*   **Fields**:
    *   `ledger_id`: Unique UUID for the record.
    *   `timestamp_utc`: ISO-8601 timestamp.
    *   `tenant_id`: Organization identifier.
    *   `mission_id`: Thread identifier.
    *   `decision_id`: Execution identifier.
    *   `actor_id`: User/Operator identifier.
    *   `event_type`: Type of event (e.g., prompt_received, decision_outcome).
    *   `payload_hash`: SHA-256 over canonicalized JSON payload.
    *   `prev_ledger_hash`: Hash of the preceding record in the chain.
    *   `signature_hmac`: HMAC protecting the integrity of the row.
*   **Purpose**: Tamper evidence, ordering, and long-term audit trail.

### B. Evidence Layer (Thick Vault)
*   **Storage**: S3-based encrypted object store (handled via `vault.py`).
*   **Content**: Canonical JSON and approved raw evidence.
*   **Addressing**: Managed by `payload_hash`, `tenant_id`, and `decision_id`.
*   **Purpose**: Accurate "Replay" and Forensic analysis.

## 2. Integrity Model
### Canonicalization
Strict deterministic hashing is mandatory. Before hashing, JSON must be:
*   UTF-8 encoded only.
*   Strict alphabetical field order (recursive).
*   Compact separators: comma + colon, no spaces (RFC 8785 / JCS style).
*   Newline normalization (`\n`).
*   Null values explicitly handled.
*   `schema_version` included in all payloads.

### Chaining
Each record's `record_hash` (or `signature_hmac`) must incorporate the `prev_ledger_hash`. 
*   **Genesis**: The first record in a decision chain points to `GENESIS`.
*   **Protection**: HMAC is used for internal fast validation; asymmetric signatures (`RS256` or `Ed25519`) preferred for legal exports.

## 3. Access Control (Reveal Workflow)
*   **Mission Owner/Analyst**: Cannot directly reveal raw evidence outside authorization.
*   **Compliance/Audit Role**: Can "Reveal & Verify" and generate "Evidence Bundles."
*   **Sensitive Classes**: Require reason codes, audit events, and optional dual-approval (break-glass).

## 4. Legal Evidence Bundle
A ZIP archive (`.kosa`) containing:
1.  `ledger.json`: The signed/hashed sequence of events.
2.  `evidence/`: Folder containing raw artifacts mapped by hash.
3.  `verify.py`: Standalone Python script for offline verification.
*   **Requirement**: A third party must be able to verify authenticity without Korum infrastructure.

## 5. Storage & Retention
*   **Witness**: Retained long-term; tiny footprint.
*   **Evidence**: Policy-controlled (S3 Lifecycle). Expire/Archive based on data class and mission age.
*   **Legal Hold**: Suspends all deletion for both layers.
*   **Tombstones**: When evidence is deleted, a Witness event is written detailing the deletion policy/reason.

## 6. Engineering Principles
*   **Minimize Plaintext**: Use direct-to-vault upload patterns where possible.
*   **Audit Heartbeat**: Background service to continuously walk and verify chains.
*   **Alerting**: SIEM/monitoring integration for hash mismatches or "Broken Chain" events.
