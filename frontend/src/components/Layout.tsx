import { Outlet } from 'react-router'
import { useTranslation } from 'react-i18next'
import {
  NavigationRegular,
  SearchRegular,
  AddRegular,
} from '@fluentui/react-icons'
import { useUIStore } from '../stores'
import { Sidebar } from './Sidebar'

export default function Layout() {
  const { t } = useTranslation()
  const { sidebarOpen, toggleSidebar } = useUIStore()

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

          {/* Actions */}
          <button
            aria-label={t('common.search')}
            className="p-1.5 rounded hover:bg-bg-hover text-text-tertiary hover:text-text-secondary transition-colors duration-150"
          >
            <SearchRegular className="w-4 h-4" />
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
    </div>
  )
}
