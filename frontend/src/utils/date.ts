/**
 * 날짜 포맷팅 유틸리티.
 */

/**
 * ISO 날짜 문자열을 사용자 친화적 형식으로 변환합니다.
 *
 * @param iso - ISO 8601 날짜 문자열 또는 null.
 * @returns "Jan 1, 2026" 형식의 문자열, null이면 "—".
 */
export function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}
