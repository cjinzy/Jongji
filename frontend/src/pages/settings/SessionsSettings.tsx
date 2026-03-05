import { useTranslation } from 'react-i18next'
import {
  PhoneRegular,
  GlobeDesktopRegular,
  LaptopRegular,
  DismissRegular,
} from '@fluentui/react-icons'
import { useSessions, useRevokeSession } from '../../hooks/useSessions'

/**
 * Infer a device icon based on user agent string.
 */
function DeviceIcon({ userAgent }: { userAgent: string }) {
  const ua = userAgent.toLowerCase()
  if (ua.includes('mobile') || ua.includes('android') || ua.includes('iphone')) {
    return <PhoneRegular style={{ fontSize: 16 }} className="text-text-secondary flex-shrink-0" />
  }
  if (ua.includes('mozilla') || ua.includes('chrome') || ua.includes('safari')) {
    return <GlobeDesktopRegular style={{ fontSize: 16 }} className="text-text-secondary flex-shrink-0" />
  }
  return <LaptopRegular style={{ fontSize: 16 }} className="text-text-secondary flex-shrink-0" />
}

/**
 * Format ISO date string to relative or absolute display.
 */
function formatLastActive(isoDate: string): string {
  const date = new Date(isoDate)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return '방금 전'
  if (diffMins < 60) return `${diffMins}분 전`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}시간 전`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}일 전`
}

/**
 * Active sessions list with per-session revoke buttons.
 * Current session is highlighted with a green badge and cannot be revoked.
 */
export default function SessionsSection() {
  const { t } = useTranslation()
  const { data: sessions, isLoading, isError } = useSessions()
  const revokeMutation = useRevokeSession()

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-1">
        {t('settings.sessions', '활성 세션')}
      </h2>
      <p className="text-xs text-text-tertiary mb-5">
        {t('settings.sessionsDesc', '현재 계정에 로그인된 모든 기기를 확인하고 관리합니다.')}
      </p>

      {isLoading && (
        <p className="text-xs text-text-tertiary font-mono py-4">
          {t('common.loading', 'Loading...')}
        </p>
      )}

      {isError && (
        <p className="text-xs text-warning font-mono py-4">
          세션 목록을 불러올 수 없습니다.
        </p>
      )}

      {sessions && sessions.length === 0 && (
        <p className="text-xs text-text-tertiary font-mono py-4">
          활성 세션이 없습니다.
        </p>
      )}

      {sessions && sessions.length > 0 && (
        <ul className="space-y-2">
          {sessions.map((session) => (
            <li
              key={session.id}
              className="flex items-center gap-3 px-4 py-3 rounded-lg bg-bg-tertiary border border-border"
            >
              <DeviceIcon userAgent={session.user_agent} />

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm text-text-primary truncate">
                    {session.user_agent.length > 60
                      ? session.user_agent.slice(0, 60) + '…'
                      : session.user_agent}
                  </p>
                  {session.is_current && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-success/15 text-success border border-success/30 flex-shrink-0">
                      현재 세션
                    </span>
                  )}
                </div>
                <p className="text-xs text-text-tertiary font-mono mt-0.5">
                  {session.ip_address} · {formatLastActive(session.last_active_at)}
                </p>
              </div>

              {!session.is_current && (
                <button
                  type="button"
                  onClick={() => revokeMutation.mutate(session.id)}
                  disabled={revokeMutation.isPending}
                  title={t('settings.revokeSession', '로그아웃')}
                  className="flex-shrink-0 flex items-center gap-1 h-7 px-2.5 rounded-lg border border-border text-text-secondary hover:text-danger hover:border-danger/40 hover:bg-danger/5 text-xs transition-colors duration-100 disabled:opacity-50"
                >
                  <DismissRegular style={{ fontSize: 12 }} />
                  {t('settings.revokeSession', '로그아웃')}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
