import apiClient from './client'

export interface SearchResultItem {
  type: 'task' | 'comment'
  task_id: string
  task_number: number
  task_title: string
  project_key: string
  highlight: string
  score: number
}

export interface SearchResponse {
  items: SearchResultItem[]
  total: number
  query: string
}

export interface SearchFilters {
  project_id?: string
  tag?: string
  status?: string
}

/**
 * Full-text search across tasks and comments.
 * Returns ranked results with highlight snippets.
 */
export async function searchApi(
  query: string,
  filters?: SearchFilters,
): Promise<SearchResponse> {
  const res = await apiClient.get<SearchResponse>('/search', {
    params: { q: query, ...filters },
  })
  return res.data
}
