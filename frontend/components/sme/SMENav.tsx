'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { initials } from '@/lib/utils'

const NAV = [
  { href: '/sme/dashboard', label: 'Dashboard' },
  { href: '/sme/materials', label: 'Materials' },
  { href: '/sme/knowledge', label: 'Knowledge' },
]

export function SMENav({ name }: { name?: string }) {
  const path = usePathname()

  return (
    <header className="h-14 bg-white border-b border-[#E5E7EB] flex items-center px-6 gap-6 shrink-0">
      <Link href="/sme/dashboard" className="text-sm font-semibold text-[#1A1A1A] mr-4 shrink-0">
        Thoth <span className="text-[#6B7280] font-normal">· SME</span>
      </Link>

      <nav className="flex items-center gap-1">
        {NAV.map(({ href, label }) => {
          const active = path === href || path.startsWith(href.replace('/dashboard', '') + '/')
          return (
            <Link
              key={href}
              href={href}
              className="px-3 py-1.5 text-sm rounded transition-colors relative"
              style={{ color: active ? '#E20074' : 'rgba(26,26,26,0.7)' }}
            >
              {label}
              {active && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#E20074] rounded-t" />
              )}
            </Link>
          )
        })}
      </nav>

      <div className="ml-auto">
        <div
          className="w-8 h-8 rounded-full bg-[#E20074] flex items-center justify-center text-white text-xs font-semibold cursor-pointer"
          title={name}
        >
          {name ? initials(name) : 'S'}
        </div>
      </div>
    </header>
  )
}
