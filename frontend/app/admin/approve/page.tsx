'use client'
import { useEffect, useState } from 'react'
import { AdminSidebar } from '@/components/admin/AdminSidebar'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { getSMEs, getKnowledge, adminApproveKnowledge, rejectKnowledge } from '@/lib/api'
import { useToast } from '@/components/shared/Toast'
import { formatDate } from '@/lib/utils'
import type { SME, KnowledgeEntry } from '@/lib/types'
import { FileText, ChevronDown, ChevronUp, CheckCircle2, XCircle } from 'lucide-react'

function ApprovalCard({ entry, smeName, onApprove, onReject }: {
  entry: KnowledgeEntry
  smeName: string
  onApprove: () => void
  onReject: (reason: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden">
      <div className="px-5 py-4 flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={entry.status} />
            <span className="text-xs text-[#6B7280]">SME Approved on {formatDate(entry.updated_at)}</span>
          </div>
          <h3 className="text-sm font-semibold text-[#1A1A1A]">{entry.topic}</h3>
          <p className="text-xs text-[#6B7280]">by {smeName}</p>
        </div>
      </div>

      {/* Sources */}
      <div className="px-5 pb-3 flex flex-wrap gap-1.5">
        {entry.sources.interviews.map(id => (
          <span key={id} className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#F3F4F6] text-xs text-[#6B7280]">
            <FileText size={10} />Interview #{id.slice(-4)}
          </span>
        ))}
        {entry.sources.materials.map(id => (
          <span key={id} className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#F3F4F6] text-xs text-[#6B7280]">
            <FileText size={10} />Material #{id.slice(-4)}
          </span>
        ))}
      </div>

      {/* Content */}
      <div className="px-5 pb-4 border-t border-[#E5E7EB] pt-4">
        <div className={`text-sm text-[#1A1A1A] leading-relaxed overflow-hidden transition-all ${expanded ? '' : 'max-h-28'}`}>
          <p className="whitespace-pre-wrap">{entry.content}</p>
        </div>
        {entry.content.length > 300 && (
          <button onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-[#6B7280] mt-2 hover:text-[#1A1A1A]">
            {expanded ? <><ChevronUp size={12} />Show less</> : <><ChevronDown size={12} />Show more</>}
          </button>
        )}
      </div>

      {/* Actions */}
      <div className="px-5 py-3 border-t border-[#E5E7EB] bg-[#F9FAFB]">
        {rejecting ? (
          <div className="space-y-2">
            <textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="Reason for rejection..."
              rows={2}
              className="w-full px-3 py-2 border border-[#E5E7EB] rounded-lg text-sm outline-none focus:border-red-400 resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={async () => {
                  setLoading(true)
                  await onReject(reason)
                  setLoading(false)
                  setRejecting(false)
                }}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500 text-white text-xs font-medium hover:bg-red-600 disabled:opacity-50"
              >
                <XCircle size={13} />Confirm Reject
              </button>
              <button onClick={() => setRejecting(false)}
                className="px-3 py-1.5 rounded-lg border border-[#E5E7EB] text-xs font-medium text-[#1A1A1A] hover:bg-white">
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={async () => { setLoading(true); await onApprove(); setLoading(false) }}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-green-600 text-white text-xs font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              <CheckCircle2 size={13} />Approve
            </button>
            <button
              onClick={() => setRejecting(true)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-red-200 text-red-600 text-xs font-medium hover:bg-red-50 transition-colors"
            >
              <XCircle size={13} />Reject
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function AdminApprovePage() {
  const { show } = useToast()
  const [smes, setSmes] = useState<SME[]>([])
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getSMEs(), getKnowledge('sme_approved')]).then(([s, e]) => {
      setSmes(s); setEntries(e); setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const getSMEName = (id: string) => smes.find(s => s.sme_id === id)?.name || 'Unknown'

  const handleApprove = async (entryId: string) => {
    try {
      await adminApproveKnowledge(entryId)
      setEntries(prev => prev.filter(e => e.entry_id !== entryId))
      show('Entry approved and added to knowledge base')
    } catch (e: any) {
      if (e.status === 409) show('This entry has already been approved or is in an invalid state.', 'error')
      else show(e.message || 'Approval failed', 'error')
    }
  }

  const handleReject = async (entryId: string, reason: string) => {
    try {
      await rejectKnowledge(entryId, reason)
      setEntries(prev => prev.filter(e => e.entry_id !== entryId))
      show('Entry rejected — SME has been notified')
    } catch (e: any) {
      if (e.status === 409) show('This entry has already been rejected.', 'error')
      else show(e.message || 'Rejection failed', 'error')
    }
  }

  return (
    <div className="flex min-h-screen bg-[#F9FAFB]">
      <AdminSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-[#E5E7EB] flex items-center px-6 gap-4">
          <div className="flex items-center gap-2 flex-1">
            <h1 className="text-sm font-semibold text-[#1A1A1A]">Pending Approval</h1>
            {entries.length > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-[#E20074] text-white text-xs font-semibold">{entries.length}</span>
            )}
          </div>
          <div className="w-8 h-8 rounded-full bg-[#E20074] flex items-center justify-center text-white text-xs font-semibold">A</div>
        </header>

        <main className="flex-1 px-6 py-6 max-w-3xl space-y-4">
          {loading ? (
            [1,2].map(i => <div key={i} className="h-48 rounded-xl skeleton" />)
          ) : entries.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <CheckCircle2 size={32} className="mx-auto text-[#D1FAE5] mb-3" />
              <p className="text-sm text-[#6B7280]">All caught up — no pending approvals</p>
            </div>
          ) : (
            entries.map(e => (
              <ApprovalCard
                key={e.entry_id}
                entry={e}
                smeName={getSMEName(e.sme_id)}
                onApprove={() => handleApprove(e.entry_id)}
                onReject={(reason) => handleReject(e.entry_id, reason)}
              />
            ))
          )}
        </main>
      </div>
    </div>
  )
}
