'use client'
import { useEffect, useRef, useState } from 'react'
import { getMaterials, uploadMaterial } from '@/lib/api'
import { SMENav } from '@/components/sme/SMENav'
import { useToast } from '@/components/shared/Toast'
import { formatDate } from '@/lib/utils'
import type { Material } from '@/lib/types'
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react'

const ACCEPTED = ['application/pdf', 'text/plain', 'text/markdown']
const ACCEPTED_EXT = '.pdf,.txt,.md'
const MAX_BYTES = 10 * 1024 * 1024

function StatusChip({ status }: { status: string }) {
  const map: Record<string, { label: string; bg: string; color: string }> = {
    processed: { label: 'Processed', bg: '#D1FAE5', color: '#065F46' },
    processing: { label: 'Processing', bg: '#FEF3C7', color: '#92400E' },
    failed:     { label: 'Failed',     bg: '#FEE2E2', color: '#991B1B' },
  }
  const s = map[status] || { label: status, bg: '#F3F4F6', color: '#374151' }
  return (
    <span className="px-2 py-0.5 rounded-full text-[11px] font-medium" style={{ background: s.bg, color: s.color }}>
      {s.label}
    </span>
  )
}

export default function SMEMaterialsPage() {
  const { show } = useToast()
  const fileRef = useRef<HTMLInputElement>(null)
  const [materials, setMaterials] = useState<Material[]>([])
  const [loading, setLoading] = useState(true)
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [uploading, setUploading] = useState(false)
  const [titleError, setTitleError] = useState('')
  const [fileError, setFileError] = useState('')

  const smeName = typeof window !== 'undefined' ? sessionStorage.getItem('sme_name') || '' : ''
  const smeId   = typeof window !== 'undefined' ? sessionStorage.getItem('sme_id')   || '' : ''

  useEffect(() => {
    if (!smeId) { setLoading(false); return }
    getMaterials(smeId)
      .then(setMaterials)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [smeId])

  const validateFile = (f: File): string => {
    if (!ACCEPTED.includes(f.type) && !f.name.match(/\.(pdf|txt|md)$/i))
      return 'Only PDF, TXT, or Markdown files are accepted.'
    if (f.size > MAX_BYTES)
      return 'File must be under 10 MB.'
    return ''
  }

  const pickFile = (f: File) => {
    const err = validateFile(f)
    if (err) { setFileError(err); return }
    setFile(f)
    setFileError('')
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ''))
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) pickFile(f)
  }

  const upload = async () => {
    let hasErr = false
    if (!file)         { setFileError('Please select a file.');    hasErr = true }
    if (!title.trim()) { setTitleError('Title is required.');      hasErr = true }
    if (hasErr) return

    if (!smeId) { show('SME session not found — please log in again.', 'error'); return }

    setUploading(true)
    try {
      const mat = await uploadMaterial(smeId, file!, title.trim(), description.trim() || undefined)
      setMaterials(prev => [mat, ...prev])
      setFile(null); setTitle(''); setDescription('')
      show('Material uploaded successfully')
    } catch (e: any) {
      if (e.status === 400) show(e.message || 'Invalid file — check format and size.', 'error')
      else show(e.message || 'Upload failed', 'error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex flex-col">
      <SMENav name={smeName} />

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-[#1A1A1A]">Materials</h1>
          <p className="text-sm text-[#6B7280] mt-1">Upload reference documents to supplement your interviews during knowledge synthesis.</p>
        </div>

        {/* Upload card */}
        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 space-y-4">
          <h2 className="text-sm font-semibold text-[#1A1A1A]">Upload New Material</h2>

          {/* Drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors"
            style={{ borderColor: dragging ? '#E20074' : '#E5E7EB', background: dragging ? '#FFF0F8' : '#F9FAFB' }}
          >
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPTED_EXT}
              className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) pickFile(f); e.target.value = '' }}
            />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText size={20} className="text-[#E20074] shrink-0" />
                <span className="text-sm font-medium text-[#1A1A1A]">{file.name}</span>
                <button
                  onClick={e => { e.stopPropagation(); setFile(null); setTitle('') }}
                  className="text-[#6B7280] hover:text-[#1A1A1A]"
                >
                  <X size={14} />
                </button>
              </div>
            ) : (
              <>
                <Upload size={24} className="mx-auto text-[#9CA3AF] mb-3" />
                <p className="text-sm text-[#1A1A1A] font-medium">Drop file here or click to browse</p>
                <p className="text-xs text-[#6B7280] mt-1">PDF, TXT, Markdown · Max 10 MB</p>
              </>
            )}
          </div>
          {fileError && <p className="text-xs text-red-500">{fileError}</p>}

          {/* Title */}
          <div>
            <label className="block text-xs font-medium text-[#1A1A1A] mb-1.5">
              Title<span className="text-[#E20074] ml-0.5">*</span>
            </label>
            <input
              value={title}
              onChange={e => { setTitle(e.target.value); setTitleError('') }}
              placeholder="e.g. MEZ Trade Compliance Guidelines 2026"
              className={`w-full px-3 py-2 rounded-lg border text-sm outline-none transition-colors ${titleError ? 'border-red-400' : 'border-[#E5E7EB] focus:border-[#E20074]'}`}
            />
            {titleError && <p className="mt-1 text-xs text-red-500">{titleError}</p>}
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-[#1A1A1A] mb-1.5">
              Description <span className="text-[#6B7280] font-normal">(optional)</span>
            </label>
            <input
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Brief description of the document content"
              className="w-full px-3 py-2 rounded-lg border border-[#E5E7EB] text-sm outline-none focus:border-[#E20074] transition-colors"
            />
          </div>

          <button
            onClick={upload}
            disabled={uploading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#E20074] text-white text-sm font-medium hover:bg-[#C5006A] disabled:opacity-50 transition-colors"
          >
            {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            {uploading ? 'Uploading…' : 'Upload Material'}
          </button>
        </div>

        {/* Materials list */}
        <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-[#E5E7EB] flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#1A1A1A]">Uploaded Materials</h2>
            <span className="text-xs text-[#6B7280]">{materials.length} total</span>
          </div>

          {loading ? (
            <div className="p-5 space-y-3">
              {[1, 2].map(i => <div key={i} className="h-14 rounded-lg skeleton" />)}
            </div>
          ) : materials.length === 0 ? (
            <div className="py-14 text-center">
              <FileText size={28} className="mx-auto text-[#D1D5DB] mb-2" />
              <p className="text-sm text-[#6B7280]">No materials uploaded yet</p>
            </div>
          ) : (
            <div className="divide-y divide-[#E5E7EB]">
              {materials.map(mat => (
                <div key={mat.material_id} className="px-5 py-3.5 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[#F3F4F6] flex items-center justify-center shrink-0">
                    <FileText size={14} className="text-[#6B7280]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#1A1A1A] truncate">{mat.title}</p>
                    <p className="text-xs text-[#6B7280]">{mat.file_type} · {formatDate(mat.created_at)}</p>
                  </div>
                  <StatusChip status={mat.status} />
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
