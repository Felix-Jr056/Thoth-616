# Thoth 616 — Project Notes

## Personnel & Responsibilities

| Person | Focus | Tasks |
|--------|-------|-------|
| **A** | 基础设施 | Task 2 + Task 7 — LLM 模块统一、所有 DB Migration、模型/配置层 |
| **B** | Query & 检索 | Task 3 + Task 4 — QA Cache、SME 路由精度、完整 query pipeline |
| **C** | Interview & 知识入库 | Task 1 + Task 5 + Task 6 — Interview 修复、Synthesis 修复、Token 优化、BackgroundTasks 修复 |
| **D** | 前端 | — |

---

## Person D File Ownership

### Files to implement / modify

| File | Task |
|------|------|
| `backend/app/services/query_service.py` | 完全重写 — QA cache 集成 |
| `backend/app/services/qa_cache_service.py` | 新增 |
| `backend/app/services/retrieval_service.py` | 加 SME fallback 逻辑 |
| `backend/app/repositories/qa_cache_repository.py` | 新增 |
| `backend/app/repositories/sme_repository.py` | 加 `list_all` 用于 fallback |
| `backend/app/routers/query.py` | 基本不变，确认 `usage` 字段 |
| `backend/app/prompts/sme_prompt.v2.md` | 优化路由 prompt |
| `backend/app/prompts/answer_generate.v3.md` | 加入 QA cache context 的 prompt 版本 |

### Off-limits files (owned by A or C)

| File | Note |
|------|------|
| `backend/app/routers/knowledge.py` | C 的文件 — D 不直接修改 |

### Coordination point

D 在 `qa_cache_service.py` 里实现 `invalidate_by_entry(entry_id)` 方法，完成后通知 C，由 C 在 `knowledge.py` 的 `PUT` 和 `reject` 端点中调用该方法。D 不直接修改 `knowledge.py`。
