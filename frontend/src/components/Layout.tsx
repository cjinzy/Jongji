import { useCallback, useEffect, useState } from 'react'
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

export default function Layout() {
  const { t } = useTranslation()
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const [paletteOpen, setPaletteOpen] = useState(false)

  const openPalette = useCallback(() => setPaletteOpen(true), [])
  const closePalette = useCallback(() => setPaletteOpen(false), [])

  // Global Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const isMac = navigator.platform.toUpperCase().includes('MAC')
      const modifier = isMac ? e.metaKey : e.ctrlKey
      if (modifier && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-primary">
      {/* Sidebar */}
      <div
        style={{ width: sidebarOpen ? 240 : 0 }}
        className="shrink-0 overflow-hidden transition-[width] duration-200 ease-in-out"
      >
        <div className="w-[240px] h-full">
          <Sidebar />
        </div>
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top header */}
        <header className="shrink-0 h-11 flex items-center gap-2 px-4 border-b border-border bg-bg-secondary">
          <button
            onClick={toggleSidebar}
            aria-label="Toggle sidebar"
            className="p-1.5 rounded hover:bg-bg-hover text-text-tertiary hover:text-text-secondary transition-colors duration-150"
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
            className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-border bg-bg-tertiary hover:border-border/80 hover:bg-bg-hover text-text-tertiary hover:text-text-secondary transition-colors duration-150 group"
          >
            <SearchRegular className="w-3.5 h-3.5" />
            <span className="hidden md:inline text-xs">{t('common.search')}</span>
            <kbd className="hidden md:flex items-center gap-0.5 ml-1">
              <span className="text-[10px] font-mono text-text-tertiary/60 border border-border/60 rounded px-1 py-0.5 bg-bg-primary leading-none">
                ⌘K
              </span>
            </kbd>
          </button>

          <button
            aria-label={t('task.create')}
            className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors duration-150"
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
