'use client'
import { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Send } from 'lucide-react'
import { getInterview, submitTurn, endInterview } from '@/lib/api'
import { SMENav } from '@/components/sme/SMENav'
import { useToast } from '@/components/shared/Toast'
import type { Interview, Turn } from '@/lib/types'

export default function SMEInterviewPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { show } = useToast()
  const [interview, setInterview] = useState<Interview | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [currentQuestion, setCurrentQuestion] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [ending, setEnding] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const smeName = typeof window !== 'undefined' ? sessionStorage.getItem('sme_name') || '' : ''

  useEffect(() => {
    getInterview(id).then(data => {
      setInterview(data)
      setTurns(data.turns || [])
      const last = data.turns?.[data.turns.length - 1]
      if (last?.agent_follow_up) setCurrentQuestion(last.agent_follow_up)
      else if (data.status === 'completed') setDone(true)
      else setCurrentQuestion(`Tell me about your expertise in ${data.topic}.`)
      setLoading(false)
    }).catch(() => { show('Failed to load interview', 'error'); setLoading(false) })
  }, [id, show])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [turns.length])

  const submit = async () => {
    if (!answer.trim() || submitting) return
    const text = answer.trim()
    setAnswer('')
    setSubmitting(true)
    try {
      const res = await submitTurn(id, text)
      setTurns(prev => [...prev, { ...res, sme_response: text }])
      if (res.agent_follow_up === null) { setCurrentQuestion(null); setDone(true) }
      else setCurrentQuestion(res.agent_follow_up)
    } catch (e: any) {
      show(e.message || 'Failed to submit', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex flex-col">
        <SMENav name={smeName} />
        <div className="flex-1 flex items-center justify-center">
          <div className="space-y-3 w-full max-w-xl px-4">
            {[1,2,3].map(i => <div key={i} className="h-12 rounded-lg skeleton" />)}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex flex-col">
      <SMENav name={smeName} />

      {/* Top bar */}
      <div className="bg-white border-b border-[#E5E7EB] px-6 py-3 flex items-center gap-4">
        <Link href="/sme/dashboard" className="text-[#6B7280] hover:text-[#1A1A1A] transition-colors">
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <h1 className="text-sm font-semibold text-[#1A1A1A]">{interview?.topic}</h1>
          <p className="text-xs text-[#6B7280]">Turn {turns.length} · {done ? 'Completed' : 'In Progress'}</p>
        </div>
        {!done && (
          <button
            onClick={async () => {
              setEnding(true)
              try {
                await endInterview(id)
              } catch {}
              setDone(true)
              show('Interview ended')
              setEnding(false)
            }}
            disabled={ending}
            className="px-3 py-1.5 rounded-lg border border-[#E5E7EB] text-xs font-medium text-[#1A1A1A] hover:bg-[#F9FAFB] disabled:opacity-50 transition-colors"
          >
            {ending ? 'Ending…' : 'End Interview'}
          </button>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="max-w-2xl mx-auto space-y-4">
              {/* Initial question */}
              {turns.length === 0 && currentQuestion && (
                <div className="flex flex-col items-start">
                  <span className="text-xs text-[#6B7280] mb-1.5 ml-1">AI Interviewer</span>
                  <div className="bg-[#F3F4F6] rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-[#1A1A1A] border-l-2 border-[#E20074]">
                    {currentQuestion}
                  </div>
                </div>
              )}

              {turns.map((turn, i) => (
                <div key={i} className="space-y-3">
                  {/* SME answer */}
                  <div className="flex justify-end">
                    <div className="max-w-[70%] bg-[#E20074] text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm">
                      {turn.sme_response}
                    </div>
                  </div>
                  {/* AI follow-up */}
                  {turn.agent_follow_up && (
                    <div className="flex flex-col items-start">
                      <span className="text-xs text-[#6B7280] mb-1.5 ml-1">AI Interviewer</span>
                      <div className={`bg-[#F3F4F6] rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-[#1A1A1A] ${i === turns.length - 1 ? 'border-l-2 border-[#E20074]' : ''}`}>
                        {turn.agent_follow_up}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {done && (
                <div className="text-center py-6">
                  <p className="text-sm text-[#6B7280]">Interview completed. Thank you for sharing your expertise!</p>
                  <Link href="/sme/dashboard"
                    className="mt-3 inline-block px-4 py-2 rounded-lg bg-[#E20074] text-white text-sm font-medium hover:bg-[#C5006A] transition-colors">
                    Back to Dashboard
                  </Link>
                </div>
              )}

              {submitting && (
                <div className="flex items-center gap-1.5 px-4 py-3 bg-[#F3F4F6] rounded-2xl rounded-tl-sm w-fit">
                  <span className="w-1.5 h-1.5 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          {/* Input */}
          {!done && (
            <div className="bg-white border-t border-[#E5E7EB] px-6 py-4">
              <div className="max-w-2xl mx-auto">
                <textarea
                  value={answer}
                  onChange={e => setAnswer(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) submit() }}
                  placeholder="Share your expertise in detail..."
                  rows={4}
                  className="w-full px-4 py-3 border border-[#E5E7EB] rounded-xl text-sm outline-none focus:border-[#E20074] transition-colors resize-none placeholder:text-[#9CA3AF]"
                />
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-[#9CA3AF]">{answer.length} characters · Ctrl+Enter to submit</span>
                  <button
                    onClick={submit}
                    disabled={!answer.trim() || submitting}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#E20074] text-white text-sm font-medium hover:bg-[#C5006A] disabled:opacity-50 transition-colors"
                  >
                    <Send size={14} />Submit Answer
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
