import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { searchApi, type SearchFilters, type SearchResponse } from '../api/search'

const DEBOUNCE_MS = 300
const MIN_QUERY_LENGTH = 2

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const searchKeys = {
  all: ['search'] as const,
  query: (query: string, filters?: SearchFilters) =>
    ['search', query, filters] as const,
}

// ---------------------------------------------------------------------------
// Debounce helper hook
// ---------------------------------------------------------------------------

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}

// ---------------------------------------------------------------------------
// useSearch
// ---------------------------------------------------------------------------

export interface UseSearchOptions {
  filters?: SearchFilters
  enabled?: boolean
}

/**
 * Debounced search hook backed by TanStack Query.
 * Only fires when query is at least 2 characters.
 */
export function useSearch(query: string, options: UseSearchOptions = {}) {
  const { filters, enabled = true } = options
  const debouncedQuery = useDebounce(query.trim(), DEBOUNCE_MS)

  const isEnabled =
    enabled && debouncedQuery.length >= MIN_QUERY_LENGTH

  const result = useQuery<SearchResponse>({
    queryKey: searchKeys.query(debouncedQuery, filters),
    queryFn: () => searchApi(debouncedQuery, filters),
    enabled: isEnabled,
    staleTime: 30 * 1000,
    placeholderData: (prev) => prev,
  })

  return {
    ...result,
    debouncedQuery,
    isSearching: result.isFetching,
  }
}
