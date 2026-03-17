# KorumOS System Specification Record

Classification: CONFIDENTIAL - TRADE SECRET
Created (local): 2026-03-17T15:21:59.9613886-04:00
Created (UTC): 2026-03-17T19:21:59.7737887Z
Repository: KorumOS
Branch: main
Commit: 6ee107aee2f6cf2c99bd47ae77aaac675d75c914

## Purpose

This document is a dated internal technical record of the KorumOS system as implemented in the repository at the commit listed above.

## System Scope

KorumOS is a Flask-based decision intelligence application with:

- A browser interface served from `index.html`, `js/`, and `css/`
- A Flask backend in `app.py`
- Multi-provider LLM orchestration in `engine_v2.py` and `llm_core.py`
- Sensitive-data minimization in `falcon.py`
- Persistence and audit models in `db.py`, `models.py`, and `ledger.py`
- Export and artifact generation in `exporters.py`
- Vault upload and asynchronous document processing in `vault.py` and `pipeline.py`

## Core Technical Characteristics

- Request handling is centralized in the Flask application layer and dispatches to workflow-specific reasoning logic.
- The reasoning engine is organized around sequential council execution and provider-specific adapters.
- Falcon preprocessing is used as a data-minimization layer before external model calls.
- SQLAlchemy models manage users, audit records, and persisted application state.
- Export tooling generates office-document and report artifacts from application output.
- Vault uploads use a direct-to-storage pattern and rely on an asynchronous pipeline for downstream processing.

## Files of Record

- `app.py`
- `engine_v2.py`
- `llm_core.py`
- `falcon.py`
- `db.py`
- `models.py`
- `ledger.py`
- `exporters.py`
- `vault.py`
- `pipeline.py`
- `index.html`
- `js/korum.js`
- `css/korum.css`

## Handling Notes

- This record is intended to support internal chronology, authorship, and implementation tracking.
- Maintain future records as separate dated files rather than rewriting this one in place.
- Keep this record in private storage. If shared publicly, it should not be treated as a trade-secret preservation measure.
