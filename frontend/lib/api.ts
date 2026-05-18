const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'
const KEY = process.env.NEXT_PUBLIC_API_KEY || 'thoth-secret-2026'

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      'Authorization': `Bearer ${KEY}`,
      'Content-Type': 'application/json',
      ...opts.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw Object.assign(new Error(err.detail || err.error || res.statusText), { status: res.status })
  }
  return res.json()
}

// SMEs
export const getSMEs = () => req<{ smes: import('./types').SME[] }>('/smes').then(r => r.smes)
export const getSME = (id: string) => req<import('./types').SME>(`/smes/${id}`)
export const createSME = (body: { name: string; specialization: string; sub_areas: string[]; contact_email: string }) =>
  req<import('./types').SME>('/smes', { method: 'POST', body: JSON.stringify(body) })

// Interviews
export const getInterviews = (smeId: string) =>
  req<{ interviews: import('./types').Interview[] }>(`/smes/${smeId}/interviews`).then(r => r.interviews)
export const getInterview = (id: string) => req<import('./types').Interview & { turns: import('./types').Turn[] }>(`/interviews/${id}`)
export const createInterview = (smeId: string, topic: string) =>
  req<import('./types').Interview>(`/smes/${smeId}/interviews`, { method: 'POST', body: JSON.stringify({ topic }) })
export const submitTurn = (interviewId: string, smeResponse: string) =>
  req<import('./types').Turn>(`/interviews/${interviewId}/turns`, { method: 'POST', body: JSON.stringify({ sme_response: smeResponse }) })

// Materials
export const getMaterials = (smeId: string) =>
  req<{ materials: import('./types').Material[] }>(`/smes/${smeId}/materials`).then(r => r.materials)
export const uploadMaterial = async (smeId: string, file: File, title: string, description?: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('title', title)
  if (description) form.append('description', description)
  const res = await fetch(`${BASE}/smes/${smeId}/materials`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${KEY}` },
    body: form,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<import('./types').Material>
}

// Knowledge
export const getKnowledge = (status?: string) =>
  req<{ entries: import('./types').KnowledgeEntry[] }>(`/knowledge${status ? `?status=${status}` : ''}`).then(r => r.entries)
export const getKnowledgeEntry = (id: string) => req<import('./types').KnowledgeEntry>(`/knowledge/${id}`)
export const updateKnowledge = (id: string, content: string) =>
  req<import('./types').KnowledgeEntry>(`/knowledge/${id}`, { method: 'PUT', body: JSON.stringify({ content }) })
export const approveKnowledge = (id: string) =>
  req<{ entry_id: string; status: string; approved_at: string }>(`/knowledge/${id}/approve`, { method: 'POST' })
export const adminApproveKnowledge = (id: string) =>
  req<{ entry_id: string; status: string; admin_approved_at: string }>(`/knowledge/${id}/admin-approve`, { method: 'POST' })
export const rejectKnowledge = (id: string, reason?: string) =>
  req<{ entry_id: string; status: string; rejected_at: string }>(`/knowledge/${id}/reject`, {
    method: 'POST', body: JSON.stringify({ reason: reason || null })
  })
export const synthesizeKnowledge = (smeId: string, body: { interview_ids: string[]; material_ids: string[]; topic: string }) =>
  req<import('./types').KnowledgeEntry & { usage: import('./types').UsageInfo | null }>(`/smes/${smeId}/knowledge/synthesize`, {
    method: 'POST', body: JSON.stringify(body)
  })

// Query
export const query = (question: string, sessionId: string) =>
  req<import('./types').QueryResponse>('/query', { method: 'POST', body: JSON.stringify({ question, session_id: sessionId }) })

// System
export const purge = () => req('/system/purge', { method: 'POST' })
export const reset = () => req('/system/reset', { method: 'POST' })

// UI-specific
export const endInterview = (interviewId: string) =>
  req(`/ui/sme/interviews/${interviewId}/end`, { method: 'POST' })
