# Benchmark API Specification

> **Required.** Every team must implement these API endpoints for automated benchmark evaluation. Your frontend/UI is separate — build whatever you want for the demo. This API is the standardized interface the evaluator calls to test all teams programmatically.

---

## Base URL

Your deployed prototype must expose a REST API at a publicly accessible base URL:

```
https://<your-deployment>/api/v1
```

Document this URL in your README.

---

## Authentication

Include a simple API key mechanism:

```
Authorization: Bearer <BENCHMARK_API_KEY>
```

Provide the key in your README.

---

## Endpoints

### 0. `GET /health` — Health check

Returns `200` if the API is operational. The evaluator calls this before running the benchmark to verify the deployment is reachable.

**Response `200 OK`:**

```json
{
  "status": "healthy",
  "timestamp": "2026-05-15T10:30:00Z"
}
```

---

### 1. `POST /smes` — Create an SME profile

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Full name of the SME |
| `specialization` | string | Yes | Primary area of expertise |
| `sub_areas` | string[] | Yes | List of specific sub-topics within the specialization |
| `contact_email` | string | Yes | Email address |

**Response `201 Created`:**

| Field | Type | Description |
|-------|------|-------------|
| `sme_id` | string | Unique identifier for the created profile |
| `name` | string | Echoed from request |
| `specialization` | string | Echoed from request |
| `sub_areas` | string[] | Echoed from request |
| `contact_email` | string | Echoed from request |
| `created_at` | string | ISO 8601 timestamp |

**Example:**

```json
// Request
POST /smes
{
  "name": "Dr. Elara Voss",
  "specialization": "MEZ Trade Compliance",
  "sub_areas": ["Restricted commodity transfers", "Compliance certifications"],
  "contact_email": "e.voss@mez-compliance.org"
}

// Response 201
{
  "sme_id": "sme_abc123",
  "name": "Dr. Elara Voss",
  "specialization": "MEZ Trade Compliance",
  "sub_areas": ["Restricted commodity transfers", "Compliance certifications"],
  "contact_email": "e.voss@mez-compliance.org",
  "created_at": "2026-05-15T10:30:00Z"
}
```

### 2. `GET /smes` — List all SME profiles

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `smes` | object[] | Array of SME profile objects (same fields as `POST /smes` response) |

### 3. `GET /smes/{sme_id}` — Retrieve an SME profile

**Response `200 OK`:** Same fields as the `POST /smes` response.

---

### 4. `GET /smes/{sme_id}/interviews` — List interviews for an SME

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `interviews` | object[] | Array of interview summary objects, each with `interview_id`, `topic`, `status`, `created_at` |

### 5. `POST /smes/{sme_id}/interviews` — Start an interview session

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topic` | string | Yes | The topic for this interview session |

**Response `201 Created`:**

| Field | Type | Description |
|-------|------|-------------|
| `interview_id` | string | Unique identifier for the interview |
| `sme_id` | string | The SME being interviewed |
| `topic` | string | Echoed from request |
| `status` | string | `"in_progress"` |
| `created_at` | string | ISO 8601 timestamp |

### 6. `POST /interviews/{interview_id}/turns` — Submit an interview turn

The SME's response is submitted; the system generates a follow-up question.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sme_response` | string | Yes | The SME's answer or statement for this turn |

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `turn_number` | integer | Sequential turn number (1, 2, 3, ...) |
| `sme_response` | string | Echoed from request |
| `agent_follow_up` | string \| null | The system's generated follow-up question. `null` if the interview is complete. |
| `timestamp` | string | ISO 8601 timestamp |
| `usage` | object \| null | Token usage (see [Token Usage Reporting](#token-usage-reporting)) |

**Example:**

```json
// Request
POST /interviews/int_xyz789/turns
{ "sme_response": "MCC Article 14 defines a restricted transfer violation as requiring four elements..." }

// Response 200
{
  "turn_number": 1,
  "sme_response": "MCC Article 14 defines a restricted transfer violation as requiring four elements...",
  "agent_follow_up": "Could you walk me through each of those four elements in detail?",
  "timestamp": "2026-05-15T10:35:00Z",
  "usage": { "prompt_tokens": 450, "completion_tokens": 32, "total_tokens": 482, "model": "claude-sonnet-4-20250514" }
}
```

### 7. `GET /interviews/{interview_id}` — Retrieve full interview transcript

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `interview_id` | string | |
| `sme_id` | string | |
| `topic` | string | |
| `status` | string | `"in_progress"` or `"completed"` |
| `turns` | object[] | Array of turn objects, each with `turn_number`, `sme_response`, `agent_follow_up`, `timestamp` |

---

### 8. `POST /smes/{sme_id}/materials` — Upload supporting material

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF or text file |
| `title` | string | Yes | Document title |
| `description` | string | No | Brief description |

**File constraints:**
- **Accepted formats:** `application/pdf`, `text/plain`, `text/markdown`
- **Maximum file size:** 10 MB
- **Reject** other file types with `400` and a clear error message

**Response `201 Created`:**

| Field | Type | Description |
|-------|------|-------------|
| `material_id` | string | Unique identifier |
| `sme_id` | string | |
| `title` | string | Echoed from request |
| `file_type` | string | MIME type (e.g., `application/pdf`) |
| `status` | string | `"processed"`, `"processing"`, or `"failed"` |
| `created_at` | string | ISO 8601 timestamp |

**Processing:** If your system processes materials asynchronously (status `"processing"`), the evaluator will poll `GET /smes/{sme_id}/materials` every 2 seconds (up to 30 seconds) until the material status transitions to `"processed"` before proceeding to synthesis. If you process synchronously, return `"processed"` directly.

### 9. `GET /smes/{sme_id}/materials` — List materials for an SME

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `materials` | object[] | Array of material objects, each with `material_id`, `title`, `file_type`, `status`, `created_at` |

---

### 10. `POST /smes/{sme_id}/knowledge/synthesize` — Trigger knowledge synthesis

Synthesizes a knowledge entry from interviews and/or uploaded materials.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `interview_ids` | string[] | Yes | IDs of interviews to synthesize from |
| `material_ids` | string[] | Yes | IDs of materials to synthesize from (can be empty) |
| `topic` | string | Yes | Topic label for the synthesized entry |

**Response `201 Created`:**

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | string | Unique identifier for the knowledge entry |
| `sme_id` | string | |
| `topic` | string | Echoed from request |
| `status` | string | `"draft"` |
| `content` | string | The synthesized text |
| `sources` | object | `{ "interviews": string[], "materials": string[] }` — IDs of source data |
| `created_at` | string | ISO 8601 timestamp |
| `usage` | object \| null | Token usage (see [Token Usage Reporting](#token-usage-reporting)) |

---

### 11. `GET /knowledge` — List all knowledge entries

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `entries` | object[] | Array of knowledge entry objects (same fields as `GET /knowledge/{entry_id}`) |

Optionally support query parameter `?status=approved` to filter by status.

### 12. `GET /knowledge/{entry_id}` — Retrieve a knowledge entry

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | string | |
| `sme_id` | string | |
| `topic` | string | |
| `status` | string | `"draft"`, `"sme_approved"`, `"approved"`, or `"rejected"` |
| `content` | string | The knowledge text |
| `sources` | object | `{ "interviews": string[], "materials": string[] }` |
| `created_at` | string | ISO 8601 timestamp |
| `updated_at` | string | ISO 8601 timestamp |

### 13. `PUT /knowledge/{entry_id}` — Edit a knowledge entry

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Updated text content |

**Response `200 OK`:** Updated knowledge entry (same fields as `GET /knowledge/{entry_id}`).

### 14. `POST /knowledge/{entry_id}/approve` — SME approves a draft entry

Changes the entry status from `"draft"` to `"sme_approved"`.

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | string | |
| `status` | string | `"sme_approved"` |
| `approved_at` | string | ISO 8601 timestamp |

### 15. `POST /knowledge/{entry_id}/admin-approve` — Admin validates an SME-approved entry

Changes the entry status from `"sme_approved"` to `"approved"`. Only entries with status `"sme_approved"` can be admin-approved. Knowledge becomes active in the knowledge base only after this step.

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | string | |
| `status` | string | `"approved"` |
| `admin_approved_at` | string | ISO 8601 timestamp |

### 16. `POST /knowledge/{entry_id}/reject` — Reject a knowledge entry

Changes the entry status to `"rejected"`. Can be called on entries in any status except `"rejected"`.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | No | Reason for rejection |

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | string | |
| `status` | string | `"rejected"` |
| `rejected_at` | string | ISO 8601 timestamp |

---

### Knowledge Entry State Transitions

```
draft → sme_approved → approved
  ↓         ↓             ↓
  rejected  rejected      rejected
```

**Invalid transitions return `409 Conflict`:**
- `/approve` on an entry that is not `"draft"` → `409`
- `/admin-approve` on an entry that is not `"sme_approved"` → `409`
- `/approve` or `/admin-approve` on a `"rejected"` entry → `409`

---

### 17. `POST /query` — Ask a question

This single endpoint handles grounded Q&A, clarifying follow-ups, and routing/escalation. The `response_type` field indicates which behavior occurred.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | The user's question |
| `session_id` | string | Yes | Session identifier for multi-turn conversations. Subsequent queries with the same `session_id` maintain conversational context (required for clarification follow-ups). |

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | The system's response text |
| `grounded` | boolean | `true` if the answer is derived from approved knowledge; `false` otherwise |
| `sources` | object[] | Array of source references, each with `entry_id`, `sme_name`, `topic`. Empty if not grounded. |
| `disclaimer` | string \| null | Disclaimer text (e.g., "This is not professional advice"), if applicable |
| `session_id` | string | Echoed from request |
| `response_type` | string | One of: `"answer"`, `"clarification"`, `"routing"` (see below) |
| `routed_to` | object[] \| null | Present only when `response_type` is `"routing"`. Array of routing targets (see below). |
| `timestamp` | string | ISO 8601 timestamp |
| `usage` | object \| null | Token usage (see [Token Usage Reporting](#token-usage-reporting)) |

---

## Response Type Field

The `response_type` field in the `/query` response is critical for automated scoring:

| Value | Meaning |
|-------|---------|
| `"answer"` | Direct answer grounded in approved knowledge |
| `"clarification"` | System is asking the user a clarifying question before answering |
| `"routing"` | System is routing the user to an SME or administrator |

## Routed-To Array

When `response_type` is `"routing"`, the `routed_to` array contains one or more routing targets. Each object:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"sme"` or `"admin"` |
| `sme_name` | string \| null | Name of the recommended SME, or `null` if escalating to admin |
| `specialization` | string | The specialization area the question falls under |
| `reason` | string | Why the system is routing to this target |

**Examples:**

```json
// Example 1: Grounded answer
POST /query
{ "question": "What are the four elements of a restricted transfer violation?", "session_id": "s1" }

// Response 200
{
  "answer": "Under MCC Article 14, a restricted transfer violation requires four elements: (a) ...",
  "grounded": true,
  "sources": [{ "entry_id": "ke_001", "sme_name": "Dr. Elara Voss", "topic": "MEZ trade compliance" }],
  "disclaimer": "This information is based on approved expert knowledge and does not constitute professional advice.",
  "session_id": "s1",
  "response_type": "answer",
  "routed_to": null,
  "timestamp": "2026-05-15T11:00:00Z",
  "usage": { "prompt_tokens": 800, "completion_tokens": 150, "total_tokens": 950, "model": "claude-sonnet-4-20250514" }
}

// Example 2: Routing to a single SME
POST /query
{ "question": "How do I file a dispute with the MEZ Tribunal?", "session_id": "s2" }

// Response 200
{
  "answer": "I don't have detailed information about tribunal filing procedures in my knowledge base, but I can direct you to the right expert.",
  "grounded": false,
  "sources": [],
  "disclaimer": null,
  "session_id": "s2",
  "response_type": "routing",
  "routed_to": [
    { "type": "sme", "sme_name": "Dr. Nadia Okafor", "specialization": "MEZ Dispute Resolution & Arbitration", "reason": "This question falls under dispute resolution procedures (Articles 42-48)." }
  ],
  "timestamp": "2026-05-15T11:01:00Z",
  "usage": { "prompt_tokens": 600, "completion_tokens": 80, "total_tokens": 680, "model": "claude-sonnet-4-20250514" }
}

// Example 3: Routing to multiple SMEs
POST /query
{ "question": "What compliance rules apply when shipping encryption hardware containing a registered algorithm?", "session_id": "s3" }

// Response 200
{
  "answer": "This question spans two specializations. I recommend consulting both experts.",
  "grounded": false,
  "sources": [],
  "disclaimer": null,
  "session_id": "s3",
  "response_type": "routing",
  "routed_to": [
    { "type": "sme", "sme_name": "Dr. Elara Voss", "specialization": "MEZ Trade Compliance", "reason": "Encryption hardware is a Category B item subject to restricted transfer rules." },
    { "type": "sme", "sme_name": "Marcus Tanaka", "specialization": "MEZ Digital Asset Protections", "reason": "Registered algorithms are protected under Article 33-35." }
  ],
  "timestamp": "2026-05-15T11:02:00Z",
  "usage": { "prompt_tokens": 700, "completion_tokens": 120, "total_tokens": 820, "model": "claude-sonnet-4-20250514" }
}

// Example 4: Clarification
POST /query
{ "question": "What are the compliance requirements?", "session_id": "s4" }

// Response 200
{
  "answer": "Could you clarify which compliance area you're asking about? I have knowledge about MEZ Trade Compliance (Articles 12-18) and MEZ Digital Asset Protections (Articles 31-37).",
  "grounded": false,
  "sources": [],
  "disclaimer": null,
  "session_id": "s4",
  "response_type": "clarification",
  "routed_to": null,
  "timestamp": "2026-05-15T11:03:00Z",
  "usage": { "prompt_tokens": 500, "completion_tokens": 45, "total_tokens": 545, "model": "claude-sonnet-4-20250514" }
}
```

---

## Token Usage Reporting

Every API response that triggers one or more LLM calls **must** include a top-level `usage` object:

| Field | Type | Description |
|-------|------|-------------|
| `prompt_tokens` | integer | Total input tokens sent to the LLM across all calls for this request |
| `completion_tokens` | integer | Total output tokens received from the LLM across all calls for this request |
| `total_tokens` | integer | Sum of prompt + completion tokens |
| `model` | string | The model ID used (e.g., `claude-sonnet-4-20250514`, `gpt-4o`) |

**Rules:**
- If a single API request triggers multiple LLM calls (e.g., a chain or tool-use loop), **sum all token counts** for that request
- If an endpoint does not involve an LLM call, the `usage` field should be `null` or omitted
- If different models are used within a single request, report the primary model and sum the tokens

**Optional:** Include a `model_breakdown` array for per-model detail:

| Field | Type | Description |
|-------|------|-------------|
| `model_breakdown` | object[] | Each object has `model` (string), `prompt_tokens` (int), `completion_tokens` (int) |

**Which endpoints must report usage:**

| Endpoint | `usage` required? |
|----------|-------------------|
| `GET /health` | No |
| `POST /smes` | No |
| `GET /smes` | No |
| `GET /smes/{id}` | No |
| `GET /smes/{id}/interviews` | No |
| `POST /smes/{id}/interviews` | Yes, if LLM is called |
| `POST /interviews/{id}/turns` | **Yes** |
| `GET /interviews/{id}` | No |
| `POST /smes/{id}/materials` | Yes, if LLM is called |
| `GET /smes/{id}/materials` | No |
| `POST /smes/{id}/knowledge/synthesize` | **Yes** |
| `GET /knowledge` | No |
| `GET /knowledge/{id}` | No |
| `PUT /knowledge/{id}` | No |
| `POST /knowledge/{id}/approve` | No |
| `POST /knowledge/{id}/admin-approve` | No |
| `POST /knowledge/{id}/reject` | No |
| `POST /query` | **Yes** |
| `POST /system/purge` | No |
| `POST /system/reset` | No |

The evaluator sums `total_tokens` across all API calls during the benchmark to compute each team's total token cost.

---

## System Endpoints

Two system endpoints are required:

### `POST /system/purge` — Wipe everything

Deletes ALL data: SME profiles, interviews, materials, knowledge entries, and query sessions.

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"purged"` |
| `message` | string | Confirmation message |

### `POST /system/reset` — Clear session state only

Clears conversation/session state only. Everything else is **preserved**:

| Data | Preserved? |
|------|-----------|
| SME profiles | Yes |
| Interviews | Yes |
| Materials | Yes |
| Knowledge entries (all statuses) | Yes |
| Conversation/session context | **No — cleared** |

The purpose of this endpoint is to test **persistence**: after a reset, the system should still answer questions from its stored knowledge base without relying on in-context conversation history.

**Response `200 OK`:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"reset"` |
| `message` | string | Confirmation message |

---

## Response Conventions

### Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `400` | Bad request (missing/invalid fields, unsupported file type, file too large) |
| `404` | Resource not found |
| `409` | Conflict (invalid state transition, e.g., `/admin-approve` on a `"draft"` entry) |
| `500` | Internal server error |

### Error Response

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Human-readable error message |
| `code` | string | Machine-readable error code (optional) |

### Content Types

- Request bodies: `application/json` (except file uploads: `multipart/form-data`)
- Responses: `application/json`

---

## Implementation Notes

- **This API is for benchmark evaluation only.** Your frontend/UI does not need to use these endpoints — it can talk to your backend however you design it.
- You may add additional endpoints beyond these for your own frontend needs.
- Field names must match exactly (snake_case as shown).
- IDs can be any string format (UUID, auto-increment, etc.) as long as they're stable and returned consistently.
- `session_id` is required on `/query`. The benchmark uses it for multi-turn clarification flows — subsequent queries with the same `session_id` must maintain conversational context.
- Timestamps must be ISO 8601 format.
- The API has **17 endpoints** plus 2 system endpoints and 1 health check.
