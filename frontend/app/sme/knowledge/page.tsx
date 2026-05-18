'use client'
import { useEffect, useState } from 'react'
import { getKnowledge, updateKnowledge, approveKnowledge, synthesizeKnowledge, getInterviews, getMaterials } from '@/lib/api'
import { SMENav } from '@/components/sme/SMENav'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { useToast } from '@/components/shared/Toast'
import { formatDate } from '@/lib/utils'
import type { KnowledgeEntry, Interview, Material } from '@/lib/types'
import { FileText, AlertCircle, CheckCircle, Plus, X, Loader2 } from 'lucide-react'

function SynthesizeModal({ smeId, onClose, onCreated }: {
  smeId: string
  onClose: () => void
  onCreated: (entry: KnowledgeEntry) => void
}) {
  const { show } = useToast()
  const [topic, setTopic] = useState('')
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [materials, setMaterials] = useState<Material[]>([])
  const [selectedInterviews, setSelectedInterviews] = useState<string[]>([])
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([])
  const [fetchLoading, setFetchLoading] = useState(true)
  const [synthesizing, setSynthesizing] = useState(false)
  const [topicError, setTopicError] = useState('')
  const [sourcesError, setSourcesError] = useState('')

  useEffect(() => {
    Promise.all([getInterviews(smeId), getMaterials(smeId)])
      .then(([ivs, mats]) => { setInterviews(ivs); setMaterials(mats) })
      .catch(() => {})
      .finally(() => setFetchLoading(false))
  }, [smeId])

  const toggleInterview = (id: string) =>
    setSelectedInterviews(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const toggleMaterial = (id: string) =>
    setSelectedMaterials(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const submit = async () => {
    let hasError = false
    if (!topic.trim()) { setTopicError('Topic is required'); hasError = true }
    if (selectedInterviews.length === 0 && selectedMaterials.length === 0) {
      setSourcesError('Select at least one interview or material'); hasError = true
    }
    if (hasError) return

    setSynthesizing(true)
    try {
      const entry = await synthesizeKnowledge(smeId, {
        interview_ids: selectedInterviews,
        material_ids: selectedMaterials,
        topic: topic.trim(),
      })
      show('Knowledge entry synthesized successfully')
      onCreated(entry)
      onClose()
    } catch (e: any) {
      if (e.status === 422) show('No content available — please complete an interview first.', 'error')
      else show(e.message || 'Synthesis failed', 'error')
    } finally {
      setSynthesizing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-[500px] bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E7EB]">
          <h2 className="text-sm font-semibold text-[#1A1A1A]">Synthesize Knowledge Entry</h2>
          <button onClick={onClose} className="text-[#6B7280] hover:text-[#1A1A1A]"><X size={16} /></button>
        </div>

        <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Topic */}
          <div>
            <label className="block text-xs font-medium text-[#1A1A1A] mb-1.5">
              Topic<span className="text-[#E20074] ml-0.5">*</span>
            </label>
            <input
              value={topic}
              onChange={e => { setTopic(e.target.value); setTopicError('') }}
              placeholder="e.g. Restricted Transfer Violations"
              className={`w-full px-3 py-2 rounded-lg border text-sm outline-none transition-colors ${topicError ? 'border-red-400' : 'border-[#E5E7EB] focus:border-[#E20074]'}`}
            />
            {topicError && <p className="mt-1 text-xs text-red-500">{topicError}</p>}
          </div>

          {fetchLoading ? (
            <div className="flex items-center justify-center py-6 gap-2 text-[#6B7280]">
              <Loader2 size={16} className="animate-spin" />
              <span className="text-xs">Loading interviews and materials…</span>
            </div>
          ) : (
            <>
              {/* Interviews */}
              <div>
                <label className="block text-xs font-medium text-[#1A1A1A] mb-1.5">
                  Source Interviews
                  <span className="text-[#6B7280] font-normal ml-1">({selectedInterviews.length} selected)</span>
                </label>
                {interviews.length === 0 ? (
                  <p className="text-xs text-[#9CA3AF] py-2">No interviews available</p>
                ) : (
                  <div className="space-y-1.5 max-h-36 overflow-y-auto border border-[#E5E7EB] rounded-lg p-2">
                    {interviews.map(iv => (
                      <label key={iv.interview_id} className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-[#F9FAFB] cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedInterviews.includes(iv.interview_id)}
                          onChange={() => { toggleInterview(iv.interview_id); setSourcesError('') }}
                          className="w-3.5 h-3.5 accent-[#E20074]"
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-[#1A1A1A] truncate">{iv.topic}</p>
                          <p className="text-[11px] text-[#6B7280]">{iv.status} · {formatDate(iv.created_at)}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Materials */}
              <div>
                <label className="block text-xs font-medium text-[#1A1A1A] mb-1.5">
                  Source Materials
                  <span className="text-[#6B7280] font-normal ml-1">(optional · {selectedMaterials.length} selected)</span>
                </label>
                {materials.length === 0 ? (
                  <p className="text-xs text-[#9CA3AF] py-2">No materials uploaded</p>
                ) : (
                  <div className="space-y-1.5 max-h-36 overflow-y-auto border border-[#E5E7EB] rounded-lg p-2">
                    {materials.map(mat => (
                      <label key={mat.material_id} className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-[#F9FAFB] cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedMaterials.includes(mat.material_id)}
                          onChange={() => { toggleMaterial(mat.material_id); setSourcesError('') }}
                          className="w-3.5 h-3.5 accent-[#E20074]"
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-[#1A1A1A] truncate">{mat.title}</p>
                          <p className="text-[11px] text-[#6B7280]">{mat.file_type} · {mat.status}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {sourcesError && (
                <p className="text-xs text-red-500">{sourcesError}</p>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-[#E5E7EB]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-[#E5E7EB] text-sm font-medium text-[#1A1A1A] hover:bg-[#F9FAFB] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={synthesizing || fetchLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#E20074] text-white text-sm font-medium hover:bg-[#C5006A] disabled:opacity-50 transition-colors"
          >
            {synthesizing && <Loader2 size={13} className="animate-spin" />}
            {synthesizing ? 'Synthesizing…' : 'Synthesize'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function SMEKnowledgePage() {
  const { show } = useToast()
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [selected, setSelected] = useState<KnowledgeEntry | null>(null)
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [approving, setApproving] = useState(false)
  const [synthOpen, setSynthOpen] = useState(false)
  const smeName = typeof window !== 'undefined' ? sessionStorage.getItem('sme_name') || '' : ''
  const smeId = typeof window !== 'undefined' ? sessionStorage.getItem('sme_id') || '' : ''

  useEffect(() => {
    getKnowledge().then(all => {
      const mine = smeId ? all.filter(e => e.sme_id === smeId) : all
      setEntries(mine)
      const first = mine.find(e => ['draft', 'rejected', 'sme_approved'].includes(e.status))
      if (first) { setSelected(first); setContent(first.content) }
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [smeId])

  const select = (e: KnowledgeEntry) => { setSelected(e); setContent(e.content) }

  const save = async () => {
    if (!selected) return
    setSaving(true)
    try {
      const updated = await updateKnowledge(selected.entry_id, content)
      setEntries(prev => prev.map(e => e.entry_id === updated.entry_id ? updated : e))
      setSelected(updated)
      show('Changes saved')
    } catch (e: any) { show(e.message || 'Save failed', 'error') }
    setSaving(false)
  }

  const approve = async () => {
    if (!selected || selected.status !== 'draft') return
    setApproving(true)
    try {
      await approveKnowledge(selected.entry_id)
      const updated = { ...selected, status: 'sme_approved' as const }
      setEntries(prev => prev.map(e => e.entry_id === selected.entry_id ? updated : e))
      setSelected(updated)
      show('Entry approved — pending admin review')
    } catch (e: any) {
      if (e.status === 409) show('This entry has already been approved or is in an invalid state.', 'error')
      else show(e.message || 'Approval failed', 'error')
    }
    setApproving(false)
  }

  const handleSynthesized = (entry: KnowledgeEntry) => {
    setEntries(prev => [entry, ...prev])
    setSelected(entry)
    setContent(entry.content)
  }

  const pending = entries.filter(e => ['draft', 'rejected'].includes(e.status))
  const existing = entries.filter(e => ['approved', 'sme_approved'].includes(e.status))

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex flex-col">
      <SMENav name={smeName} />

      {synthOpen && smeId && (
        <SynthesizeModal
          smeId={smeId}
          onClose={() => setSynthOpen(false)}
          onCreated={handleSynthesized}
        />
      )}

      <div className="flex-1 flex overflow-hidden" style={{ height: 'calc(100vh - 56px)' }}>
        {/* Left panel */}
        <aside className="w-[340px] bg-white border-r border-[#E5E7EB] flex flex-col overflow-y-auto shrink-0">
          <div className="px-4 py-3 border-b border-[#E5E7EB] flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#1A1A1A]">Pending Reviews</h2>
            <button
              onClick={() => setSynthOpen(true)}
              disabled={!smeId}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#E20074] text-white text-xs font-medium hover:bg-[#C5006A] disabled:opacity-40 transition-colors"
            >
              <Plus size={12} />New Entry
            </button>
          </div>

          {loading ? (
            <div className="p-4 space-y-3">
              {[1,2].map(i => <div key={i} className="h-20 rounded-lg skeleton" />)}
            </div>
          ) : pending.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center py-12 text-center px-4">
              <CheckCircle size={28} className="text-[#D1FAE5] mb-2" />
              <p className="text-sm text-[#6B7280]">No pending reviews</p>
              <p className="text-xs text-[#9CA3AF] mt-1">Use "New Entry" to synthesize from interviews</p>
            </div>
          ) : (
            <div className="divide-y divide-[#E5E7EB]">
              {pending.map(e => (
                <button
                  key={e.entry_id}
                  onClick={() => select(e)}
                  className="w-full text-left px-4 py-3.5 hover:bg-[#F9FAFB] transition-colors"
                  style={selected?.entry_id === e.entry_id ? { borderLeft: '2px solid #E20074', paddingLeft: '14px' } : {}}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className="text-sm font-medium text-[#1A1A1A] line-clamp-1">{e.topic}</p>
                    <StatusBadge status={e.status} />
                  </div>
                  <p className="text-xs text-[#6B7280]">Updated {formatDate(e.updated_at)}</p>
                  <p className="text-xs text-[#6B7280]">
                    {(e.sources.interviews.length + e.sources.materials.length)} sources
                  </p>
                </button>
              ))}
            </div>
          )}

          {/* Existing entries */}
          {existing.length > 0 && (
            <>
              <div className="px-4 py-3 border-t border-[#E5E7EB]">
                <h2 className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Existing Entries</h2>
              </div>
              <div className="divide-y divide-[#E5E7EB]">
                {existing.map(e => (
                  <div key={e.entry_id} className="px-4 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-medium text-[#1A1A1A] line-clamp-1">{e.topic}</p>
                      <StatusBadge status={e.status} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </aside>

        {/* Right panel */}
        {selected ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Header */}
            <div className="bg-white border-b border-[#E5E7EB] px-6 py-4">
              <div className="flex items-start justify-between gap-4 mb-3">
                <h1 className="text-base font-semibold text-[#1A1A1A]">{selected.topic}</h1>
                <StatusBadge status={selected.status} />
              </div>
              <div className="flex flex-wrap gap-1.5">
                {selected.sources.interviews.map(id => (
                  <span key={id} className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#F3F4F6] text-xs text-[#6B7280]">
                    <FileText size={10} />Interview #{id.slice(-4)}
                  </span>
                ))}
                {selected.sources.materials.map(id => (
                  <span key={id} className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#F3F4F6] text-xs text-[#6B7280]">
                    <FileText size={10} />Material #{id.slice(-4)}
                  </span>
                ))}
              </div>

              {selected.status === 'rejected' && (
                <div className="mt-3 flex items-start gap-2 p-3 bg-red-50 border border-red-100 rounded-lg">
                  <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-700">Rejected by Admin: {(selected as any).rejection_reason || 'No reason provided'}</p>
                </div>
              )}
            </div>

            {/* Editor */}
            <div className="flex-1 overflow-hidden px-6 py-4">
              <textarea
                value={content}
                onChange={e => setContent(e.target.value)}
                disabled={selected.status === 'sme_approved' || selected.status === 'approved'}
                className="w-full h-full px-4 py-3 border border-[#E5E7EB] rounded-xl text-sm font-mono leading-relaxed outline-none focus:border-[#E20074] transition-colors resize-none disabled:bg-[#F9FAFB] disabled:cursor-not-allowed"
                placeholder="Knowledge content..."
              />
            </div>

            {/* Footer */}
            <div className="bg-white border-t border-[#E5E7EB] px-6 py-3 flex items-center justify-between">
              <button
                onClick={save}
                disabled={saving || selected.status === 'sme_approved'}
                className="px-4 py-2 rounded-lg border border-[#E5E7EB] text-sm font-medium text-[#1A1A1A] hover:bg-[#F9FAFB] disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
              {selected.status === 'draft' && (
                <button
                  onClick={approve}
                  disabled={approving}
                  className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  {approving ? 'Approving…' : 'Approve'}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <FileText size={32} className="mx-auto text-[#D1D5DB] mb-3" />
              <p className="text-sm text-[#6B7280]">Select an entry to review</p>
              <p className="text-xs text-[#9CA3AF] mt-1">or click "New Entry" to synthesize knowledge</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
