# Person D — Frontend Development

## Role Summary

Person D owns the entire frontend. All work is built on one principle: **every API call goes through a single unified API Client module — never fetch directly inside a component.** This way, while A/B/C are building the backend, D develops using mock data; once the backend is ready, only the API Client implementation switches from mock to real — zero changes to component code.

---

## Unified Standards (All Team Members Must Follow)

### Environment Variables

```
DATABASE_URL=postgresql+asyncpg://...
BENCHMARK_API_KEY=thoth-secret-2026
LLM_API_KEY=...              # OpenRouter key
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MINI_MODEL=openai/gpt-4.1-mini
LLM_FULL_MODEL=openai/gpt-4.1
OPENAI_API_KEY=...           # Embedding only
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1024
KB_SIMILARITY_THRESHOLD=0.70
QA_CACHE_HIT_THRESHOLD=0.93
QA_CACHE_SOFT_THRESHOLD=0.82
```

### Naming Conventions

- All DB columns, API fields, and Python variables use **snake_case**
- DB primary keys use `id` internally; external API exposes `{entity}_id` (e.g. `sme_id`, `interview_id`)
- ID format: `{prefix}_{nanoid10}`
- Timestamps: ISO 8601 with `Z` suffix

---

## Task 8 — Frontend API Alignment (Person D's Main Task)

**Scope:** All frontend API calls must conform to the API design in Part 3:

- Benchmark endpoints (no `/ui/` prefix): frontend must NOT use these directly for UI features
- All UI functionality goes through `/ui/` prefixed endpoints
- Field names must strictly match the schema (`sme_id` not `id`, `interview_id` not `id`, `agent_follow_up` not `followup`)
- Unified error handling: `409 Conflict` (duplicate approve), `422` (empty content), `404`

**Independent test:** Use a mock server (or curl scripts) to simulate all API responses in the frontend dev environment. Confirm field mapping is correct before integration.

---

## Step 1 — Type Definitions (Day 1, complete same day)

All data types are strictly defined per the API design. This is the only contract between D and A/B/C.

Create `src/types/api.ts`:

```ts
// SME
export interface SME {
  sme_id: string
  name: string
  specialization: string
  sub_areas: string[]
  contact_email: string
  created_at: string
}

// Interview
export interface Interview {
  interview_id: string
  sme_id: string
  topic: string
  status: "in_progress" | "completed"
  created_at: string
}

export interface InterviewTurn {
  turn_number: number
  sme_response: string
  agent_follow_up: string | null
  timestamp: string
  usage: UsageInfo | null
}

export interface InterviewWithTurns extends Interview {
  turns: InterviewTurn[]
}

// Material
export interface Material {
  material_id: string
  sme_id: string
  title: string
  file_type: string
  status: "processing" | "processed" | "failed"
  created_at: string
}

// Knowledge Entry
export type KnowledgeStatus = "draft" | "sme_approved" | "approved" | "rejected"

export interface KnowledgeEntry {
  entry_id: string
  sme_id: string
  topic: string
  status: KnowledgeStatus
  content: string
  sources: {
    interviews: string[]
    materials: string[]
  }
  created_at: string
  updated_at: string
}

// Query
export type ResponseType = "answer" | "clarification" | "routing"

export interface RoutingTarget {
  type: "sme" | "admin"
  sme_name: string | null
  specialization: string
  reason: string
}

export interface QueryResponse {
  answer: string
  grounded: boolean
  sources: Array<{
    entry_id: string
    sme_name: string
    topic: string
  }>
  disclaimer: string | null
  session_id: string
  response_type: ResponseType
  routed_to: RoutingTarget[] | null
  timestamp: string
  usage: UsageInfo | null
}

// Usage
export interface UsageInfo {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  model: string
}
```

> **After creating this file, share it with A/B/C for confirmation. Fix any field name mismatches immediately. Everyone uses this file as the single source of truth.**

---

## Step 2 — API Client Layer (Day 1, implementation can change later)

Create `src/api/client.ts`:

```ts
const BASE = "/api/v1"
const HEADERS = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${import.meta.env.VITE_API_KEY}`,
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, { headers: HEADERS, ...init })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw { status: res.status, ...err }
  }
  return res.json()
}

// SME
export const smeApi = {
  create: (body: { name: string; specialization: string; sub_areas: string[]; contact_email: string }) =>
    request<SME>("/smes", { method: "POST", body: JSON.stringify(body) }),
  list: () =>
    request<{ smes: SME[] }>("/smes"),
  get: (sme_id: string) =>
    request<SME>(`/smes/${sme_id}`),
}

// Interview
export const interviewApi = {
  create: (sme_id: string, topic: string) =>
    request<Interview>(`/smes/${sme_id}/interviews`, {
      method: "POST",
      body: JSON.stringify({ topic }),
    }),
  list: (sme_id: string) =>
    request<{ interviews: Interview[] }>(`/smes/${sme_id}/interviews`),
  get: (interview_id: string) =>
    request<InterviewWithTurns>(`/interviews/${interview_id}`),
  submitTurn: (interview_id: string, sme_response: string) =>
    request<InterviewTurn>(`/interviews/${interview_id}/turns`, {
      method: "POST",
      body: JSON.stringify({ sme_response }),
    }),
}

// Material
export const materialApi = {
  upload: (sme_id: string, file: File, title: string, description?: string) => {
    const form = new FormData()
    form.append("file", file)
    form.append("title", title)
    if (description) form.append("description", description)
    return fetch(`${BASE}/smes/${sme_id}/materials`, {
      method: "POST",
      headers: { Authorization: HEADERS.Authorization },
      body: form,
    }).then(r => r.json()) as Promise<Material>
  },
  list: (sme_id: string) =>
    request<{ materials: Material[] }>(`/smes/${sme_id}/materials`),
  pollUntilProcessed: async (sme_id: string, material_id: string, maxWait = 30000) => {
    const start = Date.now()
    while (Date.now() - start < maxWait) {
      const { materials } = await materialApi.list(sme_id)
      const mat = materials.find(m => m.material_id === material_id)
      if (mat?.status === "processed") return mat
      if (mat?.status === "failed") throw new Error("Material processing failed")
      await new Promise(r => setTimeout(r, 2000))
    }
    throw new Error("Material processing timeout")
  },
}

// Knowledge
export const knowledgeApi = {
  synthesize: (sme_id: string, body: { interview_ids: string[]; material_ids: string[]; topic: string }) =>
    request<KnowledgeEntry>(`/smes/${sme_id}/knowledge/synthesize`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  list: (status?: KnowledgeStatus) =>
    request<{ entries: KnowledgeEntry[] }>(`/knowledge${status ? `?status=${status}` : ""}`),
  get: (entry_id: string) =>
    request<KnowledgeEntry>(`/knowledge/${entry_id}`),
  update: (entry_id: string, content: string) =>
    request<KnowledgeEntry>(`/knowledge/${entry_id}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  approve: (entry_id: string) =>
    request<{ entry_id: string; status: string; approved_at: string }>(
      `/knowledge/${entry_id}/approve`,
      { method: "POST" }
    ),
  adminApprove: (entry_id: string) =>
    request<{ entry_id: string; status: string; admin_approved_at: string }>(
      `/knowledge/${entry_id}/admin-approve`,
      { method: "POST" }
    ),
  reject: (entry_id: string, reason?: string) =>
    request<{ entry_id: string; status: string; rejected_at: string }>(
      `/knowledge/${entry_id}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) }
    ),
}

// Query
export const queryApi = {
  ask: (question: string, session_id: string) =>
    request<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({ question, session_id }),
    }),
}

// UI-specific endpoints
export const uiApi = {
  getKpis: () =>
    request<{ pendingApprovals: number; smesOnboarded: number; approvedEntries: number }>(
      "/ui/admin/dashboard/kpis"
    ),
  getAdminSmes: (q?: string) =>
    request<any[]>(`/ui/admin/smes${q ? `?q=${q}` : ""}`),
  getAdminKnowledge: (params?: { sme_id?: string; status?: string }) =>
    request<any[]>(`/ui/admin/knowledge${params ? "?" + new URLSearchParams(params as any) : ""}`),
}
```

---

## Step 3 — Mock Layer (Day 1, used throughout development)

Create `src/api/mock.ts` with the same function signatures as `client.ts` but returning fake data:

```ts
import type { SME, Interview, KnowledgeEntry, QueryResponse } from "../types/api"

const delay = (ms = 400) => new Promise(r => setTimeout(r, ms))

const MOCK_SMES: SME[] = [
  {
    sme_id: "sme_mock001",
    name: "Dr. Elara Voss",
    specialization: "MEZ Trade Compliance",
    sub_areas: ["Restricted commodity transfers", "Compliance certifications"],
    contact_email: "e.voss@mez.org",
    created_at: "2026-05-01T10:00:00Z",
  },
  {
    sme_id: "sme_mock002",
    name: "Marcus Tanaka",
    specialization: "MEZ Digital Asset Protections",
    sub_areas: ["Registered algorithms", "Encryption standards"],
    contact_email: "m.tanaka@mez.org",
    created_at: "2026-05-02T10:00:00Z",
  },
]

const MOCK_ENTRIES: KnowledgeEntry[] = [
  {
    entry_id: "ke_mock001",
    sme_id: "sme_mock001",
    topic: "Restricted Transfer Violations",
    status: "approved",
    content: "## Summary\n\nArticle 14 defines four elements...",
    sources: { interviews: ["int_mock001"], materials: [] },
    created_at: "2026-05-03T10:00:00Z",
    updated_at: "2026-05-03T12:00:00Z",
  },
  {
    entry_id: "ke_mock002",
    sme_id: "sme_mock002",
    topic: "Algorithm Registration",
    status: "sme_approved",
    content: "## Summary\n\nArticles 33-35 cover...",
    sources: { interviews: ["int_mock002"], materials: ["mat_mock001"] },
    created_at: "2026-05-04T10:00:00Z",
    updated_at: "2026-05-04T10:00:00Z",
  },
  {
    entry_id: "ke_mock003",
    sme_id: "sme_mock001",
    topic: "Export Controls",
    status: "draft",
    content: "Draft content pending review...",
    sources: { interviews: [], materials: [] },
    created_at: "2026-05-05T10:00:00Z",
    updated_at: "2026-05-05T10:00:00Z",
  },
]

export const smeApi = {
  create: async (body: any) => {
    await delay()
    return { ...body, sme_id: `sme_${Date.now()}`, created_at: new Date().toISOString() }
  },
  list: async () => { await delay(); return { smes: MOCK_SMES } },
  get: async (id: string) => { await delay(); return MOCK_SMES.find(s => s.sme_id === id)! },
}

export const interviewApi = {
  create: async (sme_id: string, topic: string) => {
    await delay(600)
    return { interview_id: `int_${Date.now()}`, sme_id, topic, status: "in_progress" as const, created_at: new Date().toISOString() }
  },
  submitTurn: async (interview_id: string, sme_response: string) => {
    await delay(1200)
    return {
      turn_number: 1,
      sme_response,
      agent_follow_up: "Could you walk me through a concrete example of how this applies in practice?",
      timestamp: new Date().toISOString(),
      usage: { prompt_tokens: 420, completion_tokens: 38, total_tokens: 458, model: "openai/gpt-4.1-mini" },
    }
  },
  list: async (sme_id: string) => { await delay(); return { interviews: [] } },
  get: async (id: string) => { await delay(); return { interview_id: id, sme_id: "", topic: "", status: "in_progress" as const, created_at: "", turns: [] } },
}

export const knowledgeApi = {
  list: async (status?: string) => {
    await delay()
    const entries = status ? MOCK_ENTRIES.filter(e => e.status === status) : MOCK_ENTRIES
    return { entries }
  },
  get: async (id: string) => { await delay(); return MOCK_ENTRIES.find(e => e.entry_id === id)! },
  synthesize: async (sme_id: string, body: any) => {
    await delay(2000)
    return { entry_id: `ke_${Date.now()}`, sme_id, topic: body.topic, status: "draft" as const, content: "## Summary\n\nSynthesized content...", sources: body, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), usage: { prompt_tokens: 1200, completion_tokens: 480, total_tokens: 1680, model: "openai/gpt-4.1" } }
  },
  update: async (id: string, content: string) => { await delay(); return { ...MOCK_ENTRIES[0], entry_id: id, content } },
  approve: async (id: string) => { await delay(); return { entry_id: id, status: "sme_approved", approved_at: new Date().toISOString() } },
  adminApprove: async (id: string) => { await delay(); return { entry_id: id, status: "approved", admin_approved_at: new Date().toISOString() } },
  reject: async (id: string, reason?: string) => { await delay(); return { entry_id: id, status: "rejected", rejected_at: new Date().toISOString() } },
}

export const queryApi = {
  ask: async (question: string, session_id: string): Promise<QueryResponse> => {
    await delay(1500)
    // Simulates all three response types for UI testing
    if (question.toLowerCase().includes("compliance")) {
      return { answer: "Under Article 14, a restricted transfer violation requires four elements...", grounded: true, sources: [{ entry_id: "ke_mock001", sme_name: "Dr. Elara Voss", topic: "Restricted Transfer Violations" }], disclaimer: "This information is based on approved expert knowledge and does not constitute professional advice.", session_id, response_type: "answer", routed_to: null, timestamp: new Date().toISOString(), usage: { prompt_tokens: 800, completion_tokens: 150, total_tokens: 950, model: "openai/gpt-4.1" } }
    }
    if (question.toLowerCase().includes("tribunal")) {
      return { answer: "I don't have detailed information about this. Let me connect you with the right expert.", grounded: false, sources: [], disclaimer: null, session_id, response_type: "routing", routed_to: [{ type: "sme", sme_name: "Dr. Nadia Okafor", specialization: "MEZ Dispute Resolution", reason: "Tribunal procedures fall under Articles 42-48." }], timestamp: new Date().toISOString(), usage: { prompt_tokens: 600, completion_tokens: 80, total_tokens: 680, model: "openai/gpt-4.1" } }
    }
    return { answer: "Could you clarify which compliance area you're asking about? (A) Trade Compliance or (B) Digital Asset Protections?", grounded: false, sources: [], disclaimer: null, session_id, response_type: "clarification", routed_to: null, timestamp: new Date().toISOString(), usage: { prompt_tokens: 500, completion_tokens: 45, total_tokens: 545, model: "openai/gpt-4.1-mini" } }
  },
}

export const uiApi = {
  getKpis: async () => { await delay(); return { pendingApprovals: 2, smesOnboarded: 3, approvedEntries: 5 } },
  getAdminSmes: async () => { await delay(); return MOCK_SMES.map(s => ({ ...s, stats: { interviews: 2, approved: 3 } })) },
  getAdminKnowledge: async () => { await delay(); return MOCK_ENTRIES.map(e => ({ ...e, sme_name: "Dr. Elara Voss" })) },
}

export const materialApi = {
  upload: async (sme_id: string, file: File, title: string) => { await delay(800); return { material_id: `mat_${Date.now()}`, sme_id, title, file_type: file.type, status: "processed" as const, created_at: new Date().toISOString() } },
  list: async (sme_id: string) => { await delay(); return { materials: [] } },
  pollUntilProcessed: async (sme_id: string, material_id: string) => { await delay(1000); return { material_id, sme_id, title: "", file_type: "", status: "processed" as const, created_at: "" } },
}
```

---

## Step 4 — Single Switch Between Mock and Real

Create `src/api/index.ts` — the only API import entry point in the entire project:

```ts
const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"

export const { smeApi, interviewApi, materialApi, knowledgeApi, queryApi, uiApi } =
  USE_MOCK
    ? await import("./mock")
    : await import("./client")
```

- `.env.development`: `VITE_USE_MOCK=true`
- `.env.production`: `VITE_USE_MOCK=false`

All components must import like this — no other pattern allowed:

```ts
import { smeApi, queryApi } from "@/api"
```

---

## Step 5 — Page & Component Structure

Build all three role views using mock data:

```
src/
  api/
    index.ts          ← toggle switch
    client.ts         ← real implementation
    mock.ts           ← mock implementation
  types/
    api.ts            ← type definitions (build on Day 1)
  pages/
    user/
      ChatPage.tsx            ← user query chat interface
    sme/
      OnboardingPage.tsx      ← SME registration form
      InterviewPage.tsx       ← knowledge capture conversation (most complex)
      MaterialUploadPage.tsx
      KnowledgeReviewPage.tsx ← view + edit + approve
    admin/
      DashboardPage.tsx
      SMEListPage.tsx
      KnowledgeListPage.tsx
      KnowledgeDetailPage.tsx ← approve / reject actions
  components/
    chat/
      MessageBubble.tsx   ← three styles: answer / clarification / routing
      SourceCard.tsx      ← display grounded sources
      RoutingCard.tsx     ← display routed_to list
    interview/
      QuestionCard.tsx    ← display agent_follow_up
      TurnHistory.tsx     ← display turn history
      StatusBadge.tsx     ← in_progress / completed
    knowledge/
      StatusBadge.tsx     ← four color states: draft / sme_approved / approved / rejected
      ContentEditor.tsx   ← markdown editor
      ApprovalButtons.tsx ← approve / reject button group (handles 409)
```

---

## Step 6 — Questions to Confirm with A/B/C

Before development, ask these in the group chat:

1. **Interview first question:** Does the first `agent_follow_up` come back on interview creation, or only on the first turn response? The spec shows no initial question in the create response. D will display a fixed prompt ("Please share your expertise on {topic}") until the first turn returns. C confirms this behavior — no API change needed.

2. **Clarification response:** When `response_type` is `"clarification"`, the `answer` field contains the clarifying question text, `sources` is an empty array, and `routed_to` is null. D uses these fields to distinguish the three UI styles. Confirm this understanding is correct.

3. **409 handling:** When `POST /knowledge/{id}/approve` returns 409, what should the frontend display? D suggests: *"This entry has already been approved or is in an invalid state."* Ask B to confirm the `error` field format of the 409 response.

---

## Integration (When Backend Is Ready)

When A/B/C deploy to a test URL, D does exactly two things:

1. Change `.env.development` to `VITE_USE_MOCK=false`, add `VITE_API_BASE_URL=http://...`
2. Run the app, check the console for errors — 99% of issues will be field name mismatches

As long as `src/types/api.ts` was aligned with A/B/C on Day 1, integration will be nearly frictionless because all components are written against those types, and the backend is implemented against the same spec.

---

## Coordination Rules

### File Ownership — Only the Owner May Modify

| File | Owner |
|------|-------|
| `app/ai_core/*` | A |
| `app/config.py` | A |
| `app/dependencies.py` | A |
| `app/main.py` | A |
| `migrations/` | A |
| `app/services/query_service.py` | B |
| `app/services/qa_cache_service.py` | B |
| `app/services/retrieval_service.py` | B |
| `app/routers/query.py` | B |
| `app/services/interview_service.py` | C |
| `app/routers/interviews.py` | C |
| `app/routers/knowledge.py` | C |
| Frontend (`src/`) | **D** |

### Only One Cross-Person Coordination Point

B writes `QACacheService.invalidate(entry_id)` and announces the method signature in the group chat. C then adds two lines calling it in `knowledge.py`. That's the only place two people need to coordinate — everything else is fully independent.

### Before Anyone Starts — A Must Deliver First

- List of all task names in `ModelRouter` (post in group chat; B and C reference this when writing services)
- `alembic upgrade head` runs successfully (B and C need the new fields in their local environments)
- Confirm `LLMClient.call(task, inputs, response_format)` interface signature is unchanged

---

## Scoring Reference (Know What Matters)

| Metric | Weight | Relevance to D |
|--------|--------|----------------|
| Functional Capability Pass Rate | 25% | All 8 capabilities must have working UI flows |
| Context Answer Ratio | 20% | `SourceCard` must correctly display grounded sources |
| Routing Precision | 15% | `RoutingCard` must clearly display all `routed_to` targets with reasons |
| Closed-Book Failure Rate | 10% | UI must not show fabricated answers when KB is empty |
| Interview Quality | 5% | `QuestionCard` must render `agent_follow_up` faithfully |
| Synthesis Quality | 5% | Knowledge content editor must display synthesized markdown properly |
| Guardrail Effectiveness | 5% | `disclaimer` field must always be displayed when `grounded: true` |
| Response Latency | 5% | Keep UI snappy; avoid unnecessary re-renders |
| Token Efficiency | 5% | D does not directly control this, but avoid redundant API calls |
| Persistence | 5% | UI must work correctly after `/system/reset` |
