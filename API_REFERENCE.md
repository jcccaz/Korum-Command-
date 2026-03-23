# KorumOS API Reference

The **KorumOS API** is a RESTful interface for building missions, managing security policies, and auditing decision intelligence. All endpoints require authentication via session cookies or API keys, unless otherwise noted.

## 1. Authentication & Profiling

| Endpoint | Method | Description | Role |
| :--- | :--- | :--- | :--- |
| `/api/auth/register` | `POST` | Register a new user (may be limited to invite-only). | Public |
| `/api/auth/login` | `POST` | Authenticate and create a session. | Public |
| `/api/auth/logout` | `POST` | Terminate the active session. | User |
| `/api/auth/status` | `GET` | Get current user session status. | User |
| `/api/settings/profile`| `GET` | Get user profile and preferences. | User |
| `/api/settings/profile`| `POST` | Update user preferences (JSON object). | User |
| `/api/settings/password`| `POST`| Change password (requires current password). | User |

## 2. Mission Control

| Endpoint | Method | Description | Role |
| :--- | :--- | :--- | :--- |
| `/api/missions` | `GET` | List recent missions for the current user. | User |
| `/api/missions/launch` | `POST` | Start a new Council Mission. | User |
| `/api/missions/<id>` | `GET` | Get the current state/status of a mission. | User |
| `/api/missions/<id>/results`| `GET` | Read the finalized **Decision Packet** and ATL logs. | User |
| `/api/interrogate` | `POST` | Run a forensic interrogation on an AI claim. | User |

## 3. Administrative Operations (Admin Only)

These endpoints require the `admin` role and are used for system-wide governance.

| Endpoint | Method | Description | Role |
| :--- | :--- | :--- | :--- |
| `/api/admin/users` | `GET` | List all registered users and their login activity. | Admin |
| `/api/admin/users` | `POST` | Create a new user (Invite-only mode). | Admin |
| `/api/admin/users/<id>/role`| `POST` | Change a user's role (admin, compliance, user). | Admin |
| `/api/admin/falcon-config`| `GET` | Read current Falcon protected terms and hostnames. | Admin |
| `/api/admin/falcon-config`| `POST` | Update Falcon redaction rules (JSON array). | Admin |
| `/api/admin/api-status` | `GET` | Check connectivity for OpenAI, Google, Anthropic, etc. | Admin |

## 4. Audit & Compliance

| Endpoint | Method | Description | Role |
| :--- | :--- | :--- | :--- |
| `/api/auth/audit` | `GET` | Get the **Audit Trail Ledger (ATL)** for the user. | User |
| `/api/admin/audit-all` | `GET` | System-wide audit logs for security reviews. | Compliance |

## 5. Security Note: Falcon Protocol
All mission requests sent to `/api/missions/launch` are automatically passed through the **Falcon Protocol** (Pass A/B/C) before any external LLM is invoked. This process is mandatory and cannot be bypassed via the API.

---
*Produced by Korum-OS Decision Intelligence / API Spec v2.2*
