import { useState } from 'react'
import type { SortKey, SortDir } from './tableUtils'

interface UseTableSortReturn {
  sortKey: SortKey
  sortDir: SortDir
  /** Toggle direction if the same key; otherwise set new key with ascending direction. */
  handleSort: (key: SortKey) => void
}

/**
 * Manages sortKey / sortDir state for the table view.
 * Defaults to ascending by task number.
 */
export function useTableSort(): UseTableSortReturn {
  const [sortKey, setSortKey] = useState<SortKey>('number')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  return { sortKey, sortDir, handleSort }
}
