import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import {
  SearchRegular,
  DismissRegular,
  TaskListSquareLtrRegular,
  ChatRegular,
  ClockRegular,
  ArrowEnterLeftRegular,
} from '@fluentui/react-icons'
import { useSearch } from '../hooks/useSearch'
import type { SearchResultItem } from '../api/search'

// ---------------------------------------------------------------------------
// Recent searches — localStorage backed, max 5
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'jongji-recent-searches'
const MAX_RECENT = 5

function getRecentSearches(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
  } catch {
    return []
  }
}

function saveRecentSearch(query: string): void {
  const trimmed = query.trim()
  if (!trimmed) return
  const prev = getRecentSearches().filter((q) => q !== trimmed)
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify([trimmed, ...prev].slice(0, MAX_RECENT)),
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Renders text with <mark> segments highlighted.
 * The backend returns highlight strings with <mark>...</mark> tags.
 */
function HighlightText({ html }: { html: string }) {
  return (
    <span
      className="[&_mark]:bg-accent/20 [&_mark]:text-accent [&_mark]:rounded-[2px] [&_mark]:px-0.5"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

// ---------------------------------------------------------------------------
// Result item component
// ---------------------------------------------------------------------------

function ResultItem({
  item,
  isActive,
  onSelect,
  onMouseEnter,
}: {
  item: SearchResultItem
  isActive: boolean
  onSelect: (item: SearchResultItem) => void
  onMouseEnter: () => void
}) {
  const ref = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (isActive) {
      ref.current?.scrollIntoView({ block: 'nearest' })
    }
  }, [isActive])

  return (
    <button
      ref={ref}
      type="button"
      role="option"
      aria-selected={isActive}
      onClick={() => onSelect(item)}
      onMouseEnter={onMouseEnter}
      className={`w-full flex items-start gap-3 px-4 py-2.5 text-left transition-colors duration-75 outline-none ${
        isActive ? 'bg-bg-hover' : 'hover:bg-bg-hover/50'
      }`}
    >
      {/* Type icon */}
      <span className="mt-0.5 shrink-0 text-text-tertiary">
        {item.type === 'task' ? (
          <TaskListSquareLtrRegular className="w-4 h-4" />
        ) : (
          <ChatRegular className="w-4 h-4" />
        )}
      </span>

      <span className="flex-1 min-w-0">
        {/* Title row */}
        <span className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-text-tertiary shrink-0 tracking-wide">
            {item.project_key}-{item.task_number}
          </span>
          <span className="text-sm text-text-primary truncate font-medium">
            {item.task_title}
          </span>
        </span>

        {/* Highlight snippet */}
        {item.highlight && item.highlight !== item.task_title && (
          <span className="block mt-0.5 text-xs text-text-tertiary truncate leading-relaxed">
            <HighlightText html={item.highlight} />
          </span>
        )}
      </span>

      {/* Enter hint */}
      {isActive && (
        <span className="shrink-0 mt-0.5 text-text-tertiary opacity-60">
          <ArrowEnterLeftRegular className="w-3.5 h-3.5" />
        </span>
      )}
    </button>
  )
}

// ---------------------------------------------------------------------------
// Section header
// ---------------------------------------------------------------------------

function SectionHeader({ label, count }: { label: string; count: number }) {
  return (
    <div className="flex items-center gap-2 px-4 py-1.5 border-t border-border first:border-t-0">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-text-tertiary select-none">
        {label}
      </span>
      <span className="text-[10px] text-text-tertiary/60 font-mono">{count}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main CommandPalette
// ---------------------------------------------------------------------------

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const [recentSearches, setRecentSearches] = useState<string[]>([])

  const { data, isSearching, debouncedQuery } = useSearch(query)

  // ---- Flat list of all results for keyboard nav ----
  const allItems: SearchResultItem[] = data?.items ?? []

  // ---- Group by type ----
  const taskItems = allItems.filter((i) => i.type === 'task')
  const commentItems = allItems.filter((i) => i.type === 'comment')

  const hasResults = allItems.length > 0
  const showRecent = query.trim().length === 0

  // ---- Reset on open ----
  useEffect(() => {
    if (open) {
      setQuery('')
      setActiveIndex(0)
      setRecentSearches(getRecentSearches())
      // Slight delay to ensure the element is mounted before focusing
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [open])

  // ---- Reset active index when results change ----
  useEffect(() => {
    setActiveIndex(0)
  }, [debouncedQuery])

  // ---- Navigate to task ----
  const handleSelect = useCallback(
    (item: SearchResultItem) => {
      saveRecentSearch(query.trim() || item.task_title)
      setRecentSearches(getRecentSearches())
      navigate(
        `/teams/current/projects/${item.project_key}/tasks/${item.task_number}`,
      )
      onClose()
    },
    [navigate, onClose, query],
  )

  // ---- Recent search click ----
  const handleRecentClick = (recent: string) => {
    setQuery(recent)
    inputRef.current?.focus()
  }

  // ---- Keyboard navigation ----
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        onClose()
        return
      }

      if (!hasResults) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIndex((i) => Math.min(i + 1, allItems.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIndex((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        const item = allItems[activeIndex]
        if (item) handleSelect(item)
      }
    },
    [hasResults, allItems, activeIndex, handleSelect, onClose],
  )

  if (!open) return null

  // Compute flat index offset for comment items (after task items)
  const commentOffset = taskItems.length

  return (
    /* Overlay */
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('search.commandPalette')}
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className="relative w-full max-w-[560px] mx-4 rounded-xl border border-border bg-bg-secondary shadow-2xl shadow-black/60 overflow-hidden"
        style={{ animation: 'palette-in 140ms cubic-bezier(0.16, 1, 0.3, 1)' }}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 h-12 border-b border-border">
          <SearchRegular
            className={`w-4 h-4 shrink-0 transition-colors duration-150 ${
              isSearching ? 'text-accent' : 'text-text-tertiary'
            }`}
          />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={hasResults}
            aria-controls="palette-listbox"
            aria-autocomplete="list"
            aria-activedescendant={
              hasResults ? `palette-item-${activeIndex}` : undefined
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('search.placeholder')}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-tertiary outline-none"
          />

          {/* Kbd hint */}
          <kbd className="hidden sm:flex items-center gap-1 shrink-0">
            <span className="px-1.5 py-0.5 text-[10px] font-mono text-text-tertiary border border-border rounded bg-bg-tertiary leading-none">
              esc
            </span>
          </kbd>

          <button
            type="button"
            onClick={onClose}
            aria-label={t('common.cancel')}
            className="shrink-0 p-1 rounded hover:bg-bg-hover text-text-tertiary hover:text-text-secondary transition-colors duration-150"
          >
            <DismissRegular className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Results list */}
        <div
          ref={listRef}
          id="palette-listbox"
          role="listbox"
          aria-label={t('search.results')}
          className="max-h-[380px] overflow-y-auto overscroll-contain"
        >
          {/* Recent searches (shown when input empty) */}
          {showRecent && recentSearches.length > 0 && (
            <div className="py-1">
              <SectionHeader label={t('search.recent')} count={recentSearches.length} />
              {recentSearches.map((recent) => (
                <button
                  key={recent}
                  type="button"
                  onClick={() => handleRecentClick(recent)}
                  className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-bg-hover/50 transition-colors duration-75"
                >
                  <ClockRegular className="w-4 h-4 shrink-0 text-text-tertiary" />
                  <span className="text-sm text-text-secondary truncate">{recent}</span>
                </button>
              ))}
            </div>
          )}

          {/* Empty state when no recent & no query */}
          {showRecent && recentSearches.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 gap-1.5">
              <SearchRegular className="w-7 h-7 text-text-tertiary/40" />
              <p className="text-sm text-text-tertiary">{t('search.emptyHint')}</p>
            </div>
          )}

          {/* Loading pulse */}
          {isSearching && !hasResults && (
            <div className="flex items-center gap-3 px-4 py-3">
              <div className="w-4 h-4 rounded-full bg-text-tertiary/20 animate-pulse" />
              <div className="flex-1 h-3 rounded bg-text-tertiary/10 animate-pulse" />
            </div>
          )}

          {/* No results */}
          {!isSearching && debouncedQuery.length >= 2 && !hasResults && (
            <div className="flex flex-col items-center justify-center py-10 gap-1.5">
              <p className="text-sm text-text-secondary">
                {t('search.noResults', { query: debouncedQuery })}
              </p>
            </div>
          )}

          {/* Tasks group */}
          {taskItems.length > 0 && (
            <div
              role="group"
              aria-label={t('search.groupTasks')}
              style={{ animationDelay: '0ms' }}
              className="results-group"
            >
              <SectionHeader label={t('search.groupTasks')} count={taskItems.length} />
              {taskItems.map((item, idx) => (
                <ResultItem
                  key={item.task_id}
                  item={item}
                  isActive={activeIndex === idx}
                  onSelect={handleSelect}
                  onMouseEnter={() => setActiveIndex(idx)}
                />
              ))}
            </div>
          )}

          {/* Comments group */}
          {commentItems.length > 0 && (
            <div
              role="group"
              aria-label={t('search.groupComments')}
              className="results-group"
            >
              <SectionHeader label={t('search.groupComments')} count={commentItems.length} />
              {commentItems.map((item, idx) => (
                <ResultItem
                  key={`comment-${item.task_id}-${idx}`}
                  item={item}
                  isActive={activeIndex === commentOffset + idx}
                  onSelect={handleSelect}
                  onMouseEnter={() => setActiveIndex(commentOffset + idx)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer hint */}
        {hasResults && (
          <div className="flex items-center gap-4 px-4 py-2 border-t border-border bg-bg-primary/40">
            <span className="flex items-center gap-1.5 text-[10px] text-text-tertiary">
              <kbd className="px-1.5 py-0.5 font-mono border border-border rounded bg-bg-tertiary leading-none">↑↓</kbd>
              {t('search.hintNavigate')}
            </span>
            <span className="flex items-center gap-1.5 text-[10px] text-text-tertiary">
              <kbd className="px-1.5 py-0.5 font-mono border border-border rounded bg-bg-tertiary leading-none">↵</kbd>
              {t('search.hintOpen')}
            </span>
          </div>
        )}
      </div>

      {/* Keyframe animation injected inline to avoid CSS file dependency */}
      <style>{`
        @keyframes palette-in {
          from { opacity: 0; transform: translateY(-8px) scale(0.98); }
          to   { opacity: 1; transform: translateY(0)    scale(1); }
        }
        .results-group {
          animation: palette-in 180ms cubic-bezier(0.16, 1, 0.3, 1) both;
        }
      `}</style>
    </div>
  )
}
