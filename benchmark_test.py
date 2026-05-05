#!/usr/bin/env python3
"""
Benchmark API test runner — covers all 20 endpoints from api-specification.md
Usage: python benchmark_test.py [base_url] [api_key]
"""
import sys
import json
import time
import requests

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api/v1"
API_KEY  = sys.argv[2] if len(sys.argv) > 2 else "thoth-secret-2026"
HEADERS  = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

passed = failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅  {name}")
        passed += 1
    else:
        print(f"  ❌  {name}" + (f" — {detail}" if detail else ""))
        failed += 1

def section(title):
    print(f"\n{'─'*55}\n  {title}\n{'─'*55}")

def post(path, body=None, **kw):
    return requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=body, **kw)

def get(path, **kw):
    return requests.get(f"{BASE_URL}{path}", headers=HEADERS, **kw)

def put(path, body=None, **kw):
    return requests.put(f"{BASE_URL}{path}", headers=HEADERS, json=body, **kw)

# ── 0. Health ────────────────────────────────────────────────
section("0. Health check")
r = requests.get(f"{BASE_URL}/health")
check("GET /health → 200", r.status_code == 200)
d = r.json()
check("has status=healthy", d.get("status") == "healthy")
check("has timestamp", "timestamp" in d)

# ── Auth ─────────────────────────────────────────────────────
section("Auth")
r = requests.get(f"{BASE_URL}/smes")
check("no token → 401/403", r.status_code in (401, 403))
r = requests.get(f"{BASE_URL}/smes", headers={"Authorization": "Bearer wrong"})
check("bad token → 401/403", r.status_code in (401, 403))

# ── Purge (clean slate) ───────────────────────────────────────
section("System purge (clean slate)")
r = post("/system/purge")
check("POST /system/purge → 200", r.status_code == 200)
d = r.json()
check("status=purged", d.get("status") == "purged")
check("has message", "message" in d)

# ── 1. Create SME ─────────────────────────────────────────────
section("1. POST /smes — Create SME")
sme_body = {
    "name": "Dr. Elara Voss",
    "specialization": "MEZ Trade Compliance",
    "sub_areas": ["Restricted commodity transfers", "Compliance certifications"],
    "contact_email": "e.voss@mez-compliance.org",
}
r = post("/smes", sme_body)
check("POST /smes → 201", r.status_code == 201)
d = r.json()
check("has sme_id", "sme_id" in d)
check("name echoed", d.get("name") == sme_body["name"])
check("specialization echoed", d.get("specialization") == sme_body["specialization"])
check("sub_areas echoed", d.get("sub_areas") == sme_body["sub_areas"])
check("contact_email echoed", d.get("contact_email") == sme_body["contact_email"])
check("has created_at", "created_at" in d)
sme_id = d.get("sme_id", "")

# Create a second SME for routing tests
sme_body2 = {
    "name": "Marcus Tanaka",
    "specialization": "MEZ Digital Asset Protections",
    "sub_areas": ["Digital copyright", "Algorithm registration"],
    "contact_email": "m.tanaka@mez-digital.org",
}
r2 = post("/smes", sme_body2)
check("POST /smes (2nd SME) → 201", r2.status_code == 201)
sme_id2 = r2.json().get("sme_id", "")

# ── 2. List SMEs ──────────────────────────────────────────────
section("2. GET /smes — List SMEs")
r = get("/smes")
check("GET /smes → 200", r.status_code == 200)
d = r.json()
check("has smes array", isinstance(d.get("smes"), list))
check("contains created SME", any(s.get("sme_id") == sme_id for s in d.get("smes", [])))

# ── 3. Get SME ────────────────────────────────────────────────
section("3. GET /smes/{id} — Get SME")
r = get(f"/smes/{sme_id}")
check("GET /smes/{id} → 200", r.status_code == 200)
d = r.json()
check("sme_id matches", d.get("sme_id") == sme_id)
r404 = get("/smes/nonexistent-id-xyz")
check("GET /smes/bad_id → 404", r404.status_code == 404)

# ── 4. Start Interview ────────────────────────────────────────
section("4 & 5. POST /smes/{id}/interviews — Start interview")
r = post(f"/smes/{sme_id}/interviews", {"topic": "Restricted commodity transfers"})
check("POST /interviews → 201", r.status_code == 201)
d = r.json()
check("has interview_id", "interview_id" in d)
check("sme_id matches", d.get("sme_id") == sme_id)
check("topic echoed", d.get("topic") == "Restricted commodity transfers")
check("status=in_progress", d.get("status") == "in_progress")
check("has created_at", "created_at" in d)
interview_id = d.get("interview_id", "")

# ── 5. List Interviews ────────────────────────────────────────
section("4. GET /smes/{id}/interviews — List interviews")
r = get(f"/smes/{sme_id}/interviews")
check("GET /smes/{id}/interviews → 200", r.status_code == 200)
d = r.json()
check("has interviews array", isinstance(d.get("interviews"), list))
check("contains created interview", any(i.get("interview_id") == interview_id for i in d.get("interviews", [])))

# ── 6. Submit Interview Turn ──────────────────────────────────
section("6. POST /interviews/{id}/turns — Submit turn")
r = post(f"/interviews/{interview_id}/turns", {"sme_response": "MCC Article 14 defines a restricted transfer violation as requiring four elements: declaration, classification, authorization, and documentation."})
check("POST /turns → 200", r.status_code == 200)
d = r.json()
check("has turn_number", "turn_number" in d)
check("turn_number=1", d.get("turn_number") == 1)
check("sme_response echoed", "sme_response" in d)
check("has agent_follow_up", "agent_follow_up" in d)
check("has timestamp", "timestamp" in d)
check("has usage", "usage" in d and d["usage"] is not None)
if d.get("usage"):
    u = d["usage"]
    check("usage has prompt_tokens", "prompt_tokens" in u)
    check("usage has completion_tokens", "completion_tokens" in u)
    check("usage has total_tokens", "total_tokens" in u)
    check("usage has model", "model" in u)

# ── 7. Get Interview Transcript ───────────────────────────────
section("7. GET /interviews/{id} — Transcript")
r = get(f"/interviews/{interview_id}")
check("GET /interviews/{id} → 200", r.status_code == 200)
d = r.json()
check("has interview_id", "interview_id" in d)
check("has turns array", isinstance(d.get("turns"), list))
check("1 turn recorded", len(d.get("turns", [])) == 1)

# ── 8. Upload Material ────────────────────────────────────────
section("8. POST /smes/{id}/materials — Upload material")
txt_content = b"MEZ Trade compliance requires four elements for Article 14 violations: proper declaration, accurate classification, valid authorization, and complete documentation."
r = requests.post(
    f"{BASE_URL}/smes/{sme_id}/materials",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"file": ("compliance_guide.txt", txt_content, "text/plain")},
    data={"title": "MEZ Compliance Guide", "description": "Core compliance reference"},
)
check("POST /materials → 201", r.status_code == 201)
d = r.json()
check("has material_id", "material_id" in d)
check("sme_id matches", d.get("sme_id") == sme_id)
check("title echoed", d.get("title") == "MEZ Compliance Guide")
check("has file_type", "file_type" in d)
check("has status", d.get("status") in ("processed", "processing", "failed"))
check("has created_at", "created_at" in d)
material_id = d.get("material_id", "")

# Poll if processing
for _ in range(15):
    if d.get("status") == "processed":
        break
    time.sleep(2)
    r = get(f"/smes/{sme_id}/materials")
    mats = r.json().get("materials", [])
    mat = next((m for m in mats if m.get("material_id") == material_id), {})
    d["status"] = mat.get("status", d["status"])
check("material status=processed", d.get("status") == "processed")

# Reject bad file type
r = requests.post(
    f"{BASE_URL}/smes/{sme_id}/materials",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"file": ("image.png", b"fakepng", "image/png")},
    data={"title": "Bad file"},
)
check("bad file type → 400", r.status_code == 400)

# ── 9. List Materials ─────────────────────────────────────────
section("9. GET /smes/{id}/materials — List materials")
r = get(f"/smes/{sme_id}/materials")
check("GET /materials → 200", r.status_code == 200)
d = r.json()
check("has materials array", isinstance(d.get("materials"), list))
check("contains uploaded material", any(m.get("material_id") == material_id for m in d.get("materials", [])))

# ── 10. Synthesize Knowledge ──────────────────────────────────
section("10. POST /smes/{id}/knowledge/synthesize")
r = post(f"/smes/{sme_id}/knowledge/synthesize", {
    "interview_ids": [interview_id],
    "material_ids": [material_id],
    "topic": "Restricted commodity transfers",
})
check("POST /synthesize → 201", r.status_code == 201)
d = r.json()
check("has entry_id", "entry_id" in d)
check("sme_id matches", d.get("sme_id") == sme_id)
check("topic echoed", d.get("topic") == "Restricted commodity transfers")
check("status=draft", d.get("status") == "draft")
check("has content", bool(d.get("content")))
check("has sources", "sources" in d)
check("has created_at", "created_at" in d)
check("has usage", "usage" in d and d["usage"] is not None)
entry_id = d.get("entry_id", "")

# ── 11. List Knowledge ────────────────────────────────────────
section("11. GET /knowledge — List all entries")
r = get("/knowledge")
check("GET /knowledge → 200", r.status_code == 200)
d = r.json()
check("has entries array", isinstance(d.get("entries"), list))
check("contains created entry", any(e.get("entry_id") == entry_id for e in d.get("entries", [])))

# ── 12. Get Knowledge Entry ───────────────────────────────────
section("12. GET /knowledge/{id}")
r = get(f"/knowledge/{entry_id}")
check("GET /knowledge/{id} → 200", r.status_code == 200)
d = r.json()
check("entry_id matches", d.get("entry_id") == entry_id)
check("has status", "status" in d)
check("has content", "content" in d)
check("has sources", "sources" in d)
check("has created_at", "created_at" in d)
check("has updated_at", "updated_at" in d)
r404 = get("/knowledge/nonexistent-entry-xyz")
check("GET /knowledge/bad_id → 404", r404.status_code == 404)

# ── 13. Edit Knowledge Entry ──────────────────────────────────
section("13. PUT /knowledge/{id} — Edit entry")
r = put(f"/knowledge/{entry_id}", {"content": "Updated: MEZ Article 14 requires declaration, classification, authorization, and documentation."})
check("PUT /knowledge/{id} → 200", r.status_code == 200)
d = r.json()
check("content updated", "Updated:" in d.get("content", ""))

# ── 14. SME Approve ───────────────────────────────────────────
section("14. POST /knowledge/{id}/approve — SME approve")
r = post(f"/knowledge/{entry_id}/approve")
check("POST /approve → 200", r.status_code == 200)
d = r.json()
check("status=sme_approved", d.get("status") == "sme_approved")
check("has approved_at", "approved_at" in d)

# Double-approve should 409
r = post(f"/knowledge/{entry_id}/approve")
check("double approve → 409", r.status_code == 409)

# ── 15. Admin Approve ─────────────────────────────────────────
section("15. POST /knowledge/{id}/admin-approve")
r = post(f"/knowledge/{entry_id}/admin-approve")
check("POST /admin-approve → 200", r.status_code == 200)
d = r.json()
check("status=approved", d.get("status") == "approved")
check("has admin_approved_at", "admin_approved_at" in d)

# Admin-approve on draft should 409
r2 = post(f"/smes/{sme_id}/knowledge/synthesize", {
    "interview_ids": [interview_id],
    "material_ids": [material_id],
    "topic": "Test draft",
})
draft_id = r2.json().get("entry_id", "") if r2.status_code == 201 else ""
r = post(f"/knowledge/{draft_id}/admin-approve")
check("admin-approve on draft → 409", r.status_code == 409)

# ── 16. Reject ────────────────────────────────────────────────
section("16. POST /knowledge/{id}/reject")
r = post(f"/knowledge/{draft_id}/reject", {"reason": "Incomplete information"})
check("POST /reject → 200", r.status_code == 200)
d = r.json()
check("status=rejected", d.get("status") == "rejected")
check("has rejected_at", "rejected_at" in d)
# Reject already-rejected → 409
r = post(f"/knowledge/{draft_id}/reject", {})
check("double reject → 409", r.status_code == 409)

# ── 17. Query — closed book (no approved knowledge yet for sme2) ──
section("17. POST /query — Closed-book refusal")
r = post("/query", {"question": "Tell me about quantum entanglement physics", "session_id": "sess-closed-1"})
check("POST /query → 200", r.status_code == 200)
d = r.json()
check("has answer", bool(d.get("answer")))
check("has grounded", "grounded" in d)
check("has sources", "sources" in d)
check("has session_id", d.get("session_id") == "sess-closed-1")
check("has response_type", d.get("response_type") in ("answer", "clarification", "routing"))
check("has timestamp", "timestamp" in d)
check("has usage", "usage" in d and d["usage"] is not None)
check("not grounded (out of scope)", d.get("grounded") == False)

# ── 17b. Query — grounded answer ──────────────────────────────
section("17b. POST /query — Grounded answer")
r = post("/query", {"question": "What are the four elements of a restricted transfer violation under MCC Article 14?", "session_id": "sess-grounded-1"})
check("POST /query → 200", r.status_code == 200)
d = r.json()
check("response_type is answer or routing", d.get("response_type") in ("answer", "routing", "clarification"))
check("has usage", "usage" in d and d["usage"] is not None)
if d.get("response_type") == "answer":
    check("grounded=true", d.get("grounded") == True)
    check("sources non-empty", len(d.get("sources", [])) > 0)

# ── 17c. Query — clarification ────────────────────────────────
section("17c. POST /query — Clarification")
r = post("/query", {"question": "What are the compliance requirements?", "session_id": "sess-clarify-1"})
check("POST /query → 200", r.status_code == 200)
d = r.json()
check("has response_type", d.get("response_type") in ("answer", "clarification", "routing"))

# ── 17d. Query — routing ──────────────────────────────────────
section("17d. POST /query — Routing")
r = post("/query", {"question": "How do I file a dispute with the MEZ Tribunal?", "session_id": "sess-route-1"})
check("POST /query → 200", r.status_code == 200)
d = r.json()
if d.get("response_type") == "routing":
    check("routed_to is list", isinstance(d.get("routed_to"), list))
    if d.get("routed_to"):
        rt = d["routed_to"][0]
        check("routed_to has type", "type" in rt)
        check("routed_to has specialization", "specialization" in rt)
        check("routed_to has reason", "reason" in rt)
else:
    check("response_type valid", d.get("response_type") in ("answer", "clarification", "routing"))

# ── 18. System Reset ──────────────────────────────────────────
section("18. POST /system/reset — Clear sessions only")
r = post("/system/reset")
check("POST /system/reset → 200", r.status_code == 200)
d = r.json()
check("status=reset", d.get("status") == "reset")
check("has message", "message" in d)

# SMEs/knowledge still there after reset
r = get("/smes")
check("SMEs preserved after reset", any(s.get("sme_id") == sme_id for s in r.json().get("smes", [])))
r = get("/knowledge")
check("knowledge preserved after reset", any(e.get("entry_id") == entry_id for e in r.json().get("entries", [])))

# ── 19. Purge again — verify clean ───────────────────────────
section("19. POST /system/purge — Verify wipes everything")
r = post("/system/purge")
check("POST /system/purge → 200", r.status_code == 200)
r = get("/smes")
check("SMEs wiped after purge", r.json().get("smes", []) == [])
r = get("/knowledge")
check("knowledge wiped after purge", r.json().get("entries", []) == [])

# ── Summary ───────────────────────────────────────────────────
total = passed + failed
print(f"\n{'═'*55}")
print(f"  Results: {passed}/{total} passed  {'🎉' if failed == 0 else '⚠️'}")
if failed:
    print(f"  {failed} check(s) failed — review output above")
print(f"{'═'*55}\n")
sys.exit(0 if failed == 0 else 1)
