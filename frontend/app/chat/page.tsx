'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { Send, Plus, FileText, User, ArrowLeft, Mail } from 'lucide-react'
import { query } from '@/lib/api'
import { generateSessionId, formatRelative, initials, truncate } from '@/lib/utils'
import type { ChatMessage, RoutedTo, QuerySource } from '@/lib/types'

interface Conversation {
  id: string
  sessionId: string
  title: string
  messages: ChatMessage[]
  updatedAt: string
}

function SourceCard({ source }: { source: QuerySource }) {
  return (
    <div className="flex items-start gap-2.5 bg-white border border-[#E5E7EB] rounded-lg p-3 text-xs">
      <FileText size={14} className="text-[#6B7280] mt-0.5 shrink-0" />
      <div>
        <p className="font-medium text-[#1A1A1A]">{source.topic}</p>
        <p className="text-[#6B7280]">Approved expert: {source.sme_name}</p>
      </div>
    </div>
  )
}

function SMECard({ sme }: { sme: RoutedTo }) {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-3 w-52 shrink-0">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-[#E20074] flex items-center justify-center text-white text-xs font-semibold shrink-0">
          {sme.sme_name ? initials(sme.sme_name) : 'A'}
        </div>
        <div className="min-w-0">
          <p className="font-medium text-xs text-[#1A1A1A] truncate">{sme.sme_name || 'Administrator'}</p>
          <p className="text-[10px] text-[#6B7280] truncate">{sme.specialization}</p>
        </div>
      </div>
      <p className="text-[11px] text-[#6B7280] mb-2 line-clamp-2">{sme.reason}</p>
      {sme.type === 'sme' && sme.sme_name && (
        <a href={`mailto:${sme.sme_name.toLowerCase().replace(' ', '.')}@mez.org`}
          className="flex items-center gap-1 text-[11px] text-[#E20074] hover:underline">
          <Mail size={11} />Contact via email →
        </a>
      )}
    </div>
  )
}

function ChatBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[70%] bg-[#E20074] text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm">
          {msg.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-start mb-4 max-w-[80%]">
      <div className="flex items-center gap-1.5 mb-1.5">
        <div className="w-5 h-5 rounded-full bg-[#1A1A1A] flex items-center justify-center">
          <span className="text-white text-[9px] font-bold">AI</span>
        </div>
        <span className="text-[11px] text-[#6B7280]">Thoth</span>
      </div>

      <div className="bg-[#F3F4F6] text-[#1A1A1A] rounded-2xl rounded-tl-sm px-4 py-3 text-sm">
        {msg.content}
      </div>

      {(msg.disclaimer || msg.grounded) && (
        <p className="mt-1.5 text-[11px] text-[#6B7280] italic px-1">
          {msg.disclaimer || 'This information is based on approved expert knowledge and does not constitute professional advice.'}
        </p>
      )}

      {msg.response_type === 'answer' && msg.sources && msg.sources.length > 0 && (
        <div className="mt-2 flex flex-col gap-1.5 w-full">
          {msg.sources.map(s => <SourceCard key={s.entry_id} source={s} />)}
        </div>
      )}

      {msg.response_type === 'clarification' && msg.chips && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {msg.chips.map(c => (
            <button key={c}
              className="px-3 py-1 rounded-full border border-[#E5E7EB] text-xs text-[#1A1A1A] hover:bg-[#E20074] hover:text-white hover:border-[#E20074] transition-colors">
              {c}
            </button>
          ))}
        </div>
      )}

      {msg.response_type === 'routing' && msg.routed_to && (
        <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
          {msg.routed_to.map((sme, i) => <SMECard key={i} sme={sme} />)}
        </div>
      )}
    </div>
  )
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const active = conversations.find(c => c.id === activeId)

  const newChat = useCallback(() => {
    const id = Math.random().toString(36).slice(2)
    const sessionId = generateSessionId()
    const conv: Conversation = {
      id, sessionId, title: 'New Chat', messages: [], updatedAt: new Date().toISOString()
    }
    setConversations(prev => [conv, ...prev])
    setActiveId(id)
    setInput('')
  }, [])

  useEffect(() => { newChat() }, [newChat])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [active?.messages.length])

  const send = async () => {
    if (!input.trim() || loading || !active) return
    const text = input.trim()
    setInput('')

    const userMsg: ChatMessage = {
      id: Math.random().toString(36).slice(2),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    }

    setConversations(prev => prev.map(c => c.id === activeId ? {
      ...c,
      title: c.messages.length === 0 ? truncate(text, 40) : c.title,
      messages: [...c.messages, userMsg],
      updatedAt: new Date().toISOString(),
    } : c))

    setLoading(true)
    try {
      const res = await query(text, active.sessionId)
      const aiMsg: ChatMessage = {
        id: Math.random().toString(36).slice(2),
        role: 'ai',
        content: res.answer,
        response_type: res.response_type,
        grounded: res.grounded,
        sources: res.sources,
        disclaimer: res.disclaimer,
        routed_to: res.routed_to,
        chips: res.response_type === 'clarification'
          ? res.answer.match(/\[(.*?)\]/g)?.map(s => s.slice(1, -1))
            ?? ['Trade Compliance', 'Digital Assets', 'Dispute Resolution']
          : undefined,
        timestamp: res.timestamp,
      }
      setConversations(prev => prev.map(c => c.id === activeId ? {
        ...c, messages: [...c.messages, aiMsg], updatedAt: new Date().toISOString()
      } : c))
    } catch (e) {
      const errMsg: ChatMessage = {
        id: Math.random().toString(36).slice(2),
        role: 'ai',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      }
      setConversations(prev => prev.map(c => c.id === activeId ? {
        ...c, messages: [...c.messages, errMsg]
      } : c))
    } finally {
      setLoading(false)
    }
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className="flex h-screen bg-[#F9FAFB] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-[260px] bg-white border-r border-[#E5E7EB] flex flex-col shrink-0">
        <div className="p-3 border-b border-[#E5E7EB] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-[#1A1A1A]">
            <ArrowLeft size={14} className="text-[#6B7280]" />
            <span className="text-[#6B7280] font-normal">Thoth</span>
          </Link>
          <button
            onClick={newChat}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#E20074] text-white text-xs font-medium hover:bg-[#C5006A] transition-colors"
          >
            <Plus size={13} />New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {conversations.length === 0 && (
            <p className="text-xs text-[#6B7280] text-center py-8">No conversations yet</p>
          )}
          {conversations.map(c => (
            <button
              key={c.id}
              onClick={() => setActiveId(c.id)}
              className="w-full text-left px-3 py-2.5 mx-1 rounded-lg text-sm transition-colors"
              style={{
                background: c.id === activeId ? '#FFF0F8' : 'transparent',
                color: c.id === activeId ? '#E20074' : '#1A1A1A',
                width: 'calc(100% - 8px)',
              }}
            >
              <p className="truncate font-medium text-xs">{c.title}</p>
              <p className="text-[11px] text-[#6B7280] mt-0.5">{formatRelative(c.updatedAt)}</p>
            </button>
          ))}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Disclaimer bar */}
        <div className="bg-white border-b border-[#E5E7EB] px-6 py-2.5 text-center">
          <p className="text-xs text-[#6B7280]">
            Answers are based on approved expert knowledge and do not constitute professional advice
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {!active || active.messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-14 h-14 rounded-2xl bg-[#FFF0F8] flex items-center justify-center mb-4">
                <span className="text-[#E20074] text-2xl font-bold">T</span>
              </div>
              <h2 className="text-lg font-semibold text-[#1A1A1A] mb-2">Ask Thoth anything</h2>
              <p className="text-sm text-[#6B7280] max-w-sm">
                Get answers grounded in approved expert knowledge, or be routed to the right specialist.
              </p>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto">
              {active.messages.map(msg => <ChatBubble key={msg.id} msg={msg} />)}
              {loading && (
                <div className="flex items-start mb-4">
                  <div className="bg-[#F3F4F6] rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1.5">
                    <span className="w-1.5 h-1.5 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-[#6B7280] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="bg-white border-t border-[#E5E7EB] px-6 py-4">
          <div className="max-w-2xl mx-auto">
            <div className="flex items-end gap-3 bg-[#F9FAFB] border border-[#E5E7EB] rounded-xl px-4 py-3 focus-within:border-[#E20074] transition-colors">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ask a question..."
                rows={1}
                className="flex-1 bg-transparent resize-none outline-none text-sm text-[#1A1A1A] placeholder:text-[#9CA3AF] max-h-24"
                style={{ lineHeight: '1.5' }}
              />
              <button
                onClick={send}
                disabled={!input.trim() || loading}
                className="w-8 h-8 rounded-lg bg-[#E20074] flex items-center justify-center text-white hover:bg-[#C5006A] disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
              >
                <Send size={14} />
              </button>
            </div>
            <p className="text-[11px] text-[#9CA3AF] mt-1.5 text-center">
              Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
