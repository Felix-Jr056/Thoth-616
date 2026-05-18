# Backend Changes by A/B/C — Frontend Integration Reference

> This document summarizes what Person A, B, and C are building/changing on the backend.
> Use this as a reference when updating the frontend to match the real API.

---

## Person A — Infrastructure Layer

### File Ownership
- `app/ai_core/llm_client.py` — unified LLM client (replaces old `app/llm_client.py`)
- `app/ai_core/model_router.py` — task-to-model mapping
- `app/config.py` — all environment variables
- `app/dependencies.py` — dependency injection (refactored)
- `app/main.py` — startup initialization
- `migrations/` — all DB migrations

### DB Migrations (affects what fields exist)

**Migration 1 — `interviews` table gets 2 new columns:**
```sql
agenda_json          JSONB    NOT NULL DEFAULT '[]'
current_topic_index  INTEGER  NOT NULL DEFAULT 0
```

**Migration 2 — `smes` table gets 1 new column:**
```sql
embedding_status  VARCHAR  DEFAULT 'pending'  -- values: 'pending' | 'done' | 'failed'
```

**Migration 3 — new `qa_cache` table:**
```sql
CREATE TABLE qa_cache (
  id                  VARCHAR      PRIMARY KEY,
  question            TEXT         NOT NULL,
  answer              TEXT         NOT NULL,
  question_embedding  VECTOR(1024) NOT NULL,
  source_entry_ids    VARCHAR[]    NOT NULL DEFAULT '{}',
  session_id          VARCHAR      REFERENCES sessions(id) ON DELETE SET NULL,
  hit_count           INTEGER      NOT NULL DEFAULT 0,
  created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
  last_hit_at         TIMESTAMPTZ
);
```

### LLM Task Names (registered in ModelRouter)
All services must use these exact task names:

| Task Name | Model | Used By |
|-----------|-------|---------|
| `clarify_prompt` | `openai/gpt-4.1-mini` | B |
| `intent_classify` | `openai/gpt-4.1-mini` | B |
| `interview_refine_conclude` | `openai/gpt-4.1-mini` | C |
| `interview_topic` | `openai/gpt-4.1-mini` | C |
| `interview_followup` | `openai/gpt-4.1-mini` | C |
| `answer_generate` | `openai/gpt-4.1` | B |
| `sme_prompt` | `openai/gpt-4.1` | B |
| `synthesis_compose` | `openai/gpt-4.1` | C |

### What Frontend Needs to Know
- The old `app/llm_client.py` is **deleted** — no impact on frontend
- All `usage` fields in API responses are now reliably populated (Token Tracker middleware is global)
- `BENCHMARK_API_KEY=thoth-secret-2026` — use this as the Bearer token in all requests

---

## Person B — Query & Retrieval Layer

### File Ownership
- `app/services/query_service.py` — full rewrite with QA cache
- `app/services/qa_cache_service.py` — new
- `app/services/retrieval_service.py` — adds SME fallback logic
- `app/repositories/qa_cache_repository.py` — new
- `app/routers/query.py` — mostly unchanged, confirm `usage` field is present

### Key Change 1 — QA Cache in Query Pipeline

The `/query` endpoint now has a cache layer. Frontend impact:

When a question hits the cache exactly, the response `usage` field will be **`null`** (no LLM was called). Frontend must handle `usage: null` gracefully — don't crash if usage is missing.

```ts
// Handle this in your UI token counter:
if (response.usage) {
  addToTokenCount(response.usage.total_tokens)
}
// Don't assume usage is always present
```

### Key Change 2 — SME Routing Fallback

If SME embeddings haven't been computed yet (embedding_status = 'pending'), the system now falls back to returning all SMEs instead of routing to admin. This means:

- `response_type: "routing"` with real SME names will happen more often
- `routed_to` array will be populated with actual SMEs instead of `[{ type: "admin" }]`
- Frontend `RoutingCard` component should handle both `type: "sme"` and `type: "admin"` cases

### `/query` Response — Full Schema

```ts
interface QueryResponse {
  answer: string
  grounded: boolean
  sources: Array<{
    entry_id: string
    sme_name: string
    topic: string
  }>
  disclaimer: string | null   // present when grounded: true
  session_id: string
  response_type: "answer" | "clarification" | "routing"
  routed_to: Array<{
    type: "sme" | "admin"
    sme_name: string | null   // null when type is "admin"
    specialization: string
    reason: string
  }> | null
  timestamp: string
  usage: {                    // MAY BE NULL if cache hit
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
    model: string
    model_breakdown?: Array<{
      model: string
      prompt_tokens: number
      completion_tokens: number
    }>
  } | null
}
```

### UI-Specific Endpoints (B may add/confirm these)

These are NOT benchmark endpoints — they are for frontend use only, prefixed with `/ui/`:

| Method | Path | Returns |
|--------|------|---------|
| `GET` | `/ui/admin/dashboard/kpis` | `{ pendingApprovals, smesOnboarded, approvedEntries }` |
| `GET` | `/ui/admin/smes` | SME list with stats |
| `GET` | `/ui/admin/knowledge` | Knowledge list with filters |
| `GET` | `/ui/admin/knowledge/{id}` | Knowledge detail with timeline |

---

## Person C — Interview & Knowledge Ingestion Layer

### File Ownership
- `app/services/interview_service.py` — state management refactor + token optimization
- `app/services/synthesis_service.py` — adds fallback logic (fixes 422)
- `app/repositories/interview_repository.py` — adds agenda read/write
- `app/routers/interviews.py` — fixes initialization on create
- `app/routers/materials.py` — fixes BackgroundTasks
- `app/routers/knowledge.py` — synthesis fallback + cache invalidation

### Key Change 1 — Interview Creation Now Initializes State

**`POST /smes/{sme_id}/interviews`** now does more work on creation:
- Stores `agenda_json = [topic]` and `current_topic_index = 0` in DB
- Calls LLM in background to generate the first interview question
- Initializes `InterviewService._state` immediately

**Frontend impact:** After creating an interview, the first `agent_follow_up` from `POST /interviews/{id}/turns` will be a real, relevant question (not a generic fallback string). Your `InterviewPage` can remove any hardcoded "Please share your expertise..." placeholder logic if you have it.

### Key Change 2 — `POST /smes/{sme_id}/interviews` Response

```ts
interface Interview {
  interview_id: string
  sme_id: string
  topic: string
  status: "in_progress"   // always in_progress on create
  created_at: string
  // NOTE: no initial question in create response
  // first agent_follow_up comes from the first /turns call
}
```

### Key Change 3 — Synthesis No Longer Returns 422

**`POST /smes/{sme_id}/knowledge/synthesize`** now has fallback logic:

1. Uses `interview_topic_summaries` if available (best quality)
2. Falls back to raw `sme_response` from turns if summaries are empty
3. Only returns `422` if ALL sources are empty

Frontend should still handle `422` gracefully, but it will be much rarer now.

### Key Change 4 — Interview Turns Response

Each turn now uses 1–2 LLM calls instead of 2–3 (refine + conclude merged). The response shape is unchanged:

```ts
interface InterviewTurn {
  turn_number: number
  sme_response: string
  agent_follow_up: string | null  // null means interview is complete
  timestamp: string
  usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
    model: string
  } | null
}
```

When `agent_follow_up` is `null`, the interview is complete — frontend should show a "Interview Complete" state and disable the input.

### Knowledge Entry State Machine

Valid status transitions (enforced by backend, returns `409` if violated):

```
draft → sme_approved → approved
  ↓          ↓             ↓
rejected  rejected      rejected
```

| Action | Endpoint | Requires Status | Returns 409 if |
|--------|----------|-----------------|----------------|
| SME approve | `POST /knowledge/{id}/approve` | `draft` | not `draft` |
| Admin approve | `POST /knowledge/{id}/admin-approve` | `sme_approved` | not `sme_approved` |
| Reject | `POST /knowledge/{id}/reject` | any except `rejected` | already `rejected` |

**Frontend must handle 409** on approve/admin-approve buttons and show a clear error message.

### UI-Specific Endpoints (C owns these)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ui/interviews/agenda` | Generate agenda list for display |
| `POST` | `/ui/interviews/{id}/supplement` | Add info to previous topic |
| `GET` | `/ui/interviews/{id}/resume` | Resume capture progress |
| `POST` | `/ui/interviews/{id}/topics/next` | Manually advance to next topic |
| `POST` | `/ui/interviews/admin-initiate` | Admin starts a capture session |
| `POST` | `/ui/sme/interviews/{id}/end` | Manually end capture |

---

## Complete API Reference for Frontend

### Authentication
All requests need:
```
Authorization: Bearer thoth-secret-2026
Content-Type: application/json  (except file uploads)
```

### Benchmark Endpoints (all under `/api/v1`)

| Method | Path | Frontend Use |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/smes` | Create SME |
| `GET` | `/smes` | List all SMEs |
| `GET` | `/smes/{id}` | Get SME detail |
| `GET` | `/smes/{id}/interviews` | List interviews for SME |
| `POST` | `/smes/{id}/interviews` | Start new interview |
| `POST` | `/interviews/{id}/turns` | Submit answer, get follow-up |
| `GET` | `/interviews/{id}` | Get full interview with turns |
| `POST` | `/smes/{id}/materials` | Upload file (multipart) |
| `GET` | `/smes/{id}/materials` | List materials for SME |
| `POST` | `/smes/{id}/knowledge/synthesize` | Synthesize knowledge entry |
| `GET` | `/knowledge` | List all knowledge entries |
| `GET` | `/knowledge/{id}` | Get knowledge entry |
| `PUT` | `/knowledge/{id}` | Edit knowledge content |
| `POST` | `/knowledge/{id}/approve` | SME approves draft |
| `POST` | `/knowledge/{id}/admin-approve` | Admin validates entry |
| `POST` | `/knowledge/{id}/reject` | Reject entry |
| `POST` | `/query` | Ask a question |
| `POST` | `/system/purge` | Wipe all data |
| `POST` | `/system/reset` | Clear sessions only |

### Error Response Shape

```ts
interface ErrorResponse {
  error: string   // human-readable message
  code?: string   // machine-readable code (optional)
}
```

### HTTP Status Codes

| Code | Meaning | When to show what |
|------|---------|-------------------|
| `200` | Success | Normal |
| `201` | Created | After POST |
| `400` | Bad request | Show `error` field to user |
| `404` | Not found | Show "not found" state |
| `409` | Conflict | Invalid state transition — show specific message |
| `422` | Unprocessable | Content missing — tell user to add interview/material first |
| `500` | Server error | Generic error message |

---

## Summary of What Frontend Needs to Update

| Change | Component Affected | What to Do |
|--------|--------------------|------------|
| `usage` can be `null` on cache hit | Token counter / usage display | Guard with `if (usage)` check |
| `routed_to` now has real SMEs more often | `RoutingCard` | Make sure both `sme` and `admin` types render correctly |
| Interview creation initializes state | `InterviewPage` | Can remove hardcoded first-question placeholder |
| `agent_follow_up: null` = interview done | `InterviewPage` | Show "Complete" state, disable input |
| `409` on approve endpoints | `ApprovalButtons` | Catch and show clear error |
| `422` on synthesize (rare now) | `KnowledgeReviewPage` | Show "No content available, please complete interview first" |
| `disclaimer` present when `grounded: true` | `MessageBubble` (answer type) | Always render disclaimer text |
| All field names are snake_case | All components | `sme_id` not `id`, `entry_id` not `id`, `agent_follow_up` not `followUp` |
