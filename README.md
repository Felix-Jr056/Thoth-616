# Setup & Reproduction Guide

## Deployed API

| | |
|---|---|
| **Base URL** | `https://thoth-616.onrender.com/api/v1` |
| **Benchmark API Key** | `thoth-secret-2026` |
| **Authorization header** | `Authorization: Bearer thoth-secret-2026` |

Quick health check:
```bash
curl https://thoth-616.onrender.com/api/v1/health
```

---

## Run Locally (Step-by-Step)

### Prerequisites

- Python 3.12+
- A PostgreSQL 15+ database with the `pgvector` extension enabled (Supabase free tier works)
- API keys: an OpenRouter key (LLM calls) and an OpenAI key (embeddings)

### 1. Clone the repository

```bash
git clone https://github.com/your-org/Thoth_616.git
cd Thoth_616
```

### 2. Create the backend `.env` file

```bash
cp backend/.env.example backend/.env   # if available, otherwise create manually
```

Edit `backend/.env` with your credentials:

```env
# Database (Supabase connection pooler URL — port 6543 for asyncpg + PgBouncer)
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:6543/postgres

# LLM (OpenRouter — supports gpt-4.1, gpt-4.1-mini, etc.)
LLM_API_KEY=sk-or-v1-...
LLM_BASE_URL=https://openrouter.ai/api/v1
INTERVIEW_MODEL=openai/gpt-4.1-mini
SYNTHESIS_MODEL=openai/gpt-4.1
PLANNING_MODEL=openai/gpt-4.1

# Embeddings (direct OpenAI — text-embedding-3-small, 1024 dims)
OPENAI_API_KEY=sk-proj-...

# Benchmark auth key (set to any secret string you choose)
BENCHMARK_API_KEY=thoth-secret-2026
```

### 3. Run database migrations

```bash
cd backend
pip install alembic asyncpg
alembic upgrade head
```

### 4. Install dependencies and start the server

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

The API is now live at `http://localhost:8000/api/v1`.

### 5. Verify

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"healthy","timestamp":"..."}

curl -X POST http://localhost:8000/api/v1/smes \
  -H "Authorization: Bearer thoth-secret-2026" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test SME","specialization":"Privacy Law","sub_areas":["GDPR"],"contact_email":"test@test.com"}'
# → {"sme_id":"sme_...","name":"Test SME",...}
```

---

## API Quick Reference

All endpoints are under `/api/v1` with `Authorization: Bearer thoth-secret-2026`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (no auth required) |
| POST | `/smes` | Create SME profile |
| GET | `/smes` | List all SMEs |
| GET | `/smes/{id}` | Get SME profile |
| GET | `/smes/{id}/interviews` | List interviews for SME |
| POST | `/smes/{id}/interviews` | Start interview session |
| POST | `/interviews/{id}/turns` | Submit SME answer, get follow-up |
| GET | `/interviews/{id}` | Get full interview transcript |
| POST | `/smes/{id}/materials` | Upload PDF or text file |
| GET | `/smes/{id}/materials` | List materials for SME |
| POST | `/smes/{id}/knowledge/synthesize` | Synthesize knowledge from interviews + materials |
| GET | `/knowledge` | List all knowledge entries |
| GET | `/knowledge/{id}` | Get knowledge entry |
| PUT | `/knowledge/{id}` | Edit knowledge entry |
| POST | `/knowledge/{id}/approve` | SME approves draft |
| POST | `/knowledge/{id}/admin-approve` | Admin promotes to knowledge base |
| POST | `/knowledge/{id}/reject` | Reject entry |
| POST | `/query` | Ask a question (grounded Q&A, clarification, or routing) |
| POST | `/system/purge` | Wipe all data (benchmark state reset) |
| POST | `/system/reset` | Clear session state only |

See `api-specification.md` for full request/response schemas.

---

# Project Thoth Brief

---

## The Challenge

T-Mobile is exploring whether an AI agent can serve as a **living knowledge system** for subject matter experts (SMEs). Your team will build **Project Thoth**: a proof-of-concept that captures expert knowledge through structured interactions, organizes it for retrieval, and knows when to answer directly versus when to route a user to the right human expert.

This is not a production system. The goal is to demonstrate **technical feasibility** through a credible end-to-end prototype that T-Mobile leadership can evaluate for future investment.

### Domain

The system must handle **routing between different specializations** — knowing which expert to consult when a question falls outside the current knowledge base.

**Important:** Your system must clearly disclaim that it is **not providing professional advice**. It surfaces approved expert knowledge with attribution.
---

## The 8 Core Capabilities

Your prototype must demonstrate these capabilities end-to-end:

| # | Capability | Description |
|---|-----------|-------------|
| 1 | **SME Onboarding** | A new SME can be onboarded with a persistent profile (name, expertise areas, contact info). |
| 2 | **Expert Interview** | The system can interview an SME to capture topic-specific expertise through structured conversation. |
| 3 | **Material Ingestion** | The system accepts supporting materials — text documents, PDFs, and optionally links to relevant sources. |
| 4 | **Knowledge Synthesis** | The system synthesizes captured knowledge (from interviews + materials) into a draft entry for review. |
| 5 | **SME Review & Approval** | The SME can review, edit, and approve synthesized content. An admin validation step is required before knowledge becomes active in the knowledge base. |
| 6 | **Knowledge-Grounded Q&A** | A separate user can ask a question and receive an answer grounded in the approved knowledge base. |
| 7 | **Clarifying Follow-ups** | If a question is ambiguous, the agent asks a clarifying follow-up before answering. |
| 8 | **Routing & Escalation** | If the answer is not in the knowledge base, the system routes the user to the appropriate specialist(s). When multiple SMEs are relevant, the system surfaces all likely candidates. When no clear SME match exists, it escalates to an administrator. |

All 8 capabilities must be attempted. 

### Design Considerations

Beyond the 8 core capabilities, the sponsor highlighted these additional concepts that should inform your design:

- **Review dates / maintenance cycle:** Approved knowledge entries should support a review date or lightweight maintenance cycle so content can be revisited and updated over time. Implementation approach (DB-backed scheduling, manual review flags, cron triggers, etc.) is at the team's discretion.
- **Controlled source exposure:** Raw SME interview transcripts should not be directly exposed to end users in the Q&A experience. The system should distinguish between source materials that may be cited to users (e.g., approved handbooks or documents) and materials that remain internal to the knowledge workflow (e.g., raw interview content).

---

## What Success Looks Like

At the end of this hackathon, T-Mobile leadership should be able to see a live demo that makes it **believable** that:

1. An AI agent can learn from SMEs over time
2. It can answer questions directly from approved, attributed knowledge
3. It safely redirects users to the right human expert when needed
4. The human-in-the-loop approval step prevents unapproved or fabricated knowledge from reaching end users

A strong outcome also shows intelligent handling of overlapping SME areas through clarification and routing — though that is a bonus, not a strict requirement.

---

## Timeline, Milestones & Budget Gates

Each team receives an **$80 budget** for API costs, released in stages. You must **pass each checkpoint** to unlock the next budget tranche. See Canvas for check-in dates and evaluation dates.


**Budget rules:**
- Teams that fail a gate will disqualify to continue
- Unspent budget from earlier stages carries forward
- You manage your own spending within your unlocked total
- Budget is for LLM API costs

---

## Team Structure

Teams of 4 students. You organize yourselves. 
---

## Deliverables

Each team submits:

1. **Working prototype** — deployed to a public URL
2. **Benchmark API** — a standardized REST API conforming to `benchmark/api-specification.md` (see below)
3. **`ARCHITECTURE.md`** — system design, data model (ER diagram), tech stack justification, agentic engineering approach
4. **Demo script** — step-by-step walkthrough showing all capabilities in sequence
5. **Production recommendations** (1-2 pages) — what a real T-Mobile deployment would need: security, scale, multi-tenancy, data sensitivity, audit trails, cost estimation, monitoring
6. **GitHub repository** — documented, with README containing setup instructions, deployed URL, and benchmark API key
7. **Effort visualization** — a KanBan board, hours-spent log, or equivalent showing the development effort that went into the solution

---

## Tech Stack

**Your choice.** There is no prescribed tech stack. You must justify your selection in `ARCHITECTURE.md`. If you are interested in using the same tech stack as T-Mobile, please reach out to your industry mentor.

You are responsible for your own infrastructure and API costs within the $80 budget.

---

## Benchmark API Contract

All teams must implement a **standardized REST API** that the evaluator calls to run benchmark tests programmatically. This ensures fair, automated, apples-to-apples evaluation across all 15+ teams.

Your frontend/UI is completely separate — build whatever you want for the demo. The API is only for benchmark evaluation.

The specification defines endpoints for each of the 8 capabilities:

| Endpoint | Capability |
|----------|-----------|
| `GET /health` | Health check |
| `POST /smes`, `GET /smes`, `GET /smes/{id}` | 1. SME Onboarding |
| `POST /smes/{id}/interviews`, `POST /interviews/{id}/turns` | 2. Expert Interview |
| `POST /smes/{id}/materials` | 3. Material Upload |
| `POST /smes/{id}/knowledge/synthesize` | 4. Knowledge Synthesis |
| `PUT /knowledge/{id}`, `POST /knowledge/{id}/approve`, `POST /knowledge/{id}/admin-approve`, `POST /knowledge/{id}/reject` | 5. SME Review & Admin Approval |
| `POST /query` | 6. Q&A, 7. Clarification, 8. Routing |
| `POST /system/purge`, `POST /system/reset` | Benchmark state management |

See **`benchmark/api-specification.md`** for the full contract with request/response schemas.

### Token Usage Reporting

**Cost efficiency matters.** Every API response that involves an LLM call must include a `usage` object reporting token counts (`prompt_tokens`, `completion_tokens`, `total_tokens`, `model`). Since the benchmark sends identical inputs to every team, your total token consumption is directly comparable across teams.

Teams that achieve the same quality with fewer tokens — through better prompt engineering, smarter retrieval, model routing (e.g., Haiku for simple tasks, Sonnet for complex ones), or reducing unnecessary LLM calls — will score higher on the **token efficiency** metric.

---

## Benchmark

Your solution will be evaluated against a **formal benchmark** at the Week 9 initial evaluation. The benchmark has a specific protocol designed to test whether your system **actually learns from SME inputs**.


**Key metrics:**
- **Closed-Book Failure Rate** — does your system refuse to answer before data is loaded? (10%)
- **Functional Capability Pass Rate** — do the 8 capabilities work? (25%)
- **Context Answer Ratio** — do answers contain the specific facts from the provided SME materials? (20%)
- **Routing Precision** — are out-of-scope questions routed correctly? (15%)
- **Interview Quality** — are the agent's follow-up questions relevant and useful for knowledge capture? (5%)
- **Synthesis Quality** — is the synthesized knowledge coherent, accurate, and well-organized? (5%)
- **Response Latency** — how fast does your system respond? (5%)
- **Token Efficiency** — how many tokens did your system consume? (5%)
- **Persistence** — does knowledge survive a session reset? (5%)
- **Guardrail Effectiveness** — disclaimers, advice refusal, parametric leakage resistance (5%)

**The benchmark tests MVP functionality only.** UX, architecture, and demo quality are evaluated separately.

---

## Evaluation & Qualification

This is a **two-stage competitive evaluation**:

**Stage 1 — Initial Evaluation (Week 9):** All qualifying teams present a lightning demo and are scored by judges. The benchmark is run against each team's deployed prototype. Top-performing teams are selected to advance.

**Stage 2 — T-Mobile Leadership Demo (Finals Week):** Only qualifying teams present to T-Mobile leadership. 


---

## Rules

- This is a **bonus assignment** — participation is voluntary but strongly encouraged
- Teams that do not participate or do not qualify at initial evaluation receive course credit based on other coursework
- All 8 capabilities must be attempted; partial implementations are scored proportionally
- Your system must include appropriate disclaimers — it surfaces expert knowledge, not professional advice
