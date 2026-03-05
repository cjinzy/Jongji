import { useCallback, useEffect, useRef, useState } from 'react'
import { Outlet } from 'react-router'
import { useTranslation } from 'react-i18next'
import {
  NavigationRegular,
  SearchRegular,
  AddRegular,
} from '@fluentui/react-icons'
import { useUIStore } from '../stores'
import { Sidebar } from './Sidebar'
import { CommandPalette } from './CommandPalette'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'

/** Returns the current breakpoint category. */
function useBreakpoint(): 'mobile' | 'tablet' | 'desktop' {
  const [bp, setBp] = useState<'mobile' | 'tablet' | 'desktop'>(() => {
    if (window.innerWidth < 768) return 'mobile'
    if (window.innerWidth < 1024) return 'tablet'
    return 'desktop'
  })

  useEffect(() => {
    function update() {
      if (window.innerWidth < 768) setBp('mobile')
      else if (window.innerWidth < 1024) setBp('tablet')
      else setBp('desktop')
    }
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  return bp
}

export default function Layout() {
  const { t } = useTranslation()
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const [paletteOpen, setPaletteOpen] = useState(false)
  const bp = useBreakpoint()
  const overlayRef = useRef<HTMLDivElement>(null)

  const openPalette = useCallback(() => setPaletteOpen(true), [])
  const closePalette = useCallback(() => setPaletteOpen(false), [])

  // Global keyboard shortcuts (Cmd+K, c, j/k, /, 1-4, Escape)
  useKeyboardShortcuts({
    onCommandPalette: useCallback(() => setPaletteOpen((prev) => !prev), []),
    onSearch: openPalette,
    onClose: closePalette,
  })

  // Close sidebar when clicking outside overlay on mobile
  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === overlayRef.current) {
      toggleSidebar()
    }
  }

  const isMobile = bp === 'mobile'
  const isTablet = bp === 'tablet'

  // Sidebar width logic:
  // desktop: 240px when open, 0 when closed (current behaviour)
  // tablet: 56px icon-only when open, 0 when closed
  // mobile: overlay drawer — not in flow
  const sidebarWidth = isMobile
    ? 0
    : sidebarOpen
      ? isTablet
        ? 56
        : 240
      : 0

  return (
    <div className="flex h-screen w-screen overflow-hidden" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
      {/* Mobile overlay backdrop */}
      {isMobile && sidebarOpen && (
        <div
          ref={overlayRef}
          onClick={handleOverlayClick}
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          aria-hidden="true"
        />
      )}

      {/* Mobile: overlay drawer */}
      {isMobile ? (
        <div
          className={[
            'fixed top-0 left-0 h-full z-50 transition-transform duration-200 ease-in-out',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
          ].join(' ')}
          style={{ width: 240 }}
        >
          <Sidebar collapsed={false} />
        </div>
      ) : (
        /* Tablet/Desktop: in-flow sidebar */
        <div
          style={{ width: sidebarWidth }}
          className="shrink-0 overflow-hidden transition-[width] duration-200 ease-in-out"
        >
          <div style={{ width: isTablet ? 56 : 240 }} className="h-full">
            <Sidebar collapsed={isTablet} />
          </div>
        </div>
      )}

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top header */}
        <header
          className="shrink-0 h-11 flex items-center gap-2 px-4 border-b"
          style={{
            borderColor: 'var(--color-border)',
            backgroundColor: 'var(--color-bg-secondary)',
          }}
        >
          <button
            onClick={toggleSidebar}
            aria-label="Toggle sidebar"
            className="p-1.5 rounded transition-colors duration-150"
            style={{ color: 'var(--color-text-tertiary)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-bg-hover)'
              e.currentTarget.style.color = 'var(--color-text-secondary)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent'
              e.currentTarget.style.color = 'var(--color-text-tertiary)'
            }}
          >
            <NavigationRegular className="w-4 h-4" />
          </button>

          {/* Breadcrumb placeholder */}
          <div className="flex-1" />

          {/* Search trigger */}
          <button
            onClick={openPalette}
            aria-label={t('common.search')}
            aria-keyshortcuts="Meta+K Control+K"
            className="flex items-center gap-2 px-2.5 py-1 rounded-md border transition-colors duration-150"
            style={{
              borderColor: 'var(--color-border)',
              backgroundColor: 'var(--color-bg-tertiary)',
              color: 'var(--color-text-tertiary)',
            }}
          >
            <SearchRegular className="w-3.5 h-3.5" />
            <span className="hidden md:inline text-xs">{t('common.search')}</span>
            <kbd className="hidden md:flex items-center gap-0.5 ml-1">
              <span
                className="text-[10px] font-mono border rounded px-1 py-0.5 leading-none"
                style={{
                  color: 'var(--color-text-tertiary)',
                  borderColor: 'var(--color-border)',
                  backgroundColor: 'var(--color-bg-primary)',
                }}
              >
                ⌘K
              </span>
            </kbd>
          </button>

          <button
            aria-label={t('task.create')}
            className="flex items-center gap-1.5 px-3 py-1 rounded-md text-white text-sm font-medium transition-colors duration-150"
            style={{ backgroundColor: 'var(--color-accent)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-accent-hover)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--color-accent)'
            }}
          >
            <AddRegular className="w-4 h-4" />
            <span className="hidden sm:inline">{t('task.create')}</span>
          </button>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>

      {/* Command palette portal */}
      <CommandPalette open={paletteOpen} onClose={closePalette} />
    </div>
  )
}
