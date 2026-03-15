import { ClockRegular } from '@fluentui/react-icons'
import { STORAGE_KEY_RECENT_SEARCHES, MAX_RECENT_SEARCHES } from '../../constants/app'

/**
 * Reads recent searches from localStorage.
 * Returns an empty array if parsing fails.
 */
export function getRecentSearches(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY_RECENT_SEARCHES) ?? '[]')
  } catch {
    return []
  }
}

/**
 * Persists a search query to localStorage, deduplicating and capping at MAX_RECENT_SEARCHES.
 * Blank strings are ignored.
 */
export function saveRecentSearch(query: string): void {
  const trimmed = query.trim()
  if (!trimmed) return
  const prev = getRecentSearches().filter((q) => q !== trimmed)
  localStorage.setItem(
    STORAGE_KEY_RECENT_SEARCHES,
    JSON.stringify([trimmed, ...prev].slice(0, MAX_RECENT_SEARCHES)),
  )
}

interface RecentSearchesProps {
  searches: string[]
  onSelect: (query: string) => void
  sectionHeader: React.ReactNode
}

/**
 * Renders the recent-searches list shown in CommandPalette when the input is empty.
 */
export function RecentSearches({ searches, onSelect, sectionHeader }: RecentSearchesProps) {
  if (searches.length === 0) return null

  return (
    <div className="py-1">
      {sectionHeader}
      {searches.map((recent) => (
        <button
          key={recent}
          type="button"
          onClick={() => onSelect(recent)}
          className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-bg-hover/50 transition-colors duration-75"
        >
          <ClockRegular className="w-4 h-4 shrink-0 text-text-tertiary" />
          <span className="text-sm text-text-secondary truncate">{recent}</span>
        </button>
      ))}
    </div>
  )
}
