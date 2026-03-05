import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import {
  PersonRegular,
  LockClosedRegular,
  GlobeRegular,
  CheckmarkRegular,
  AlertBadgeRegular,
  LaptopRegular,
  PhoneRegular,
  GlobeDesktopRegular,
  DismissRegular,
  KeyRegular,
  ShieldLockRegular,
} from '@fluentui/react-icons'
import { useAuthStore } from '../stores/auth'
import i18n from '../i18n'
import TimePicker from '../components/TimePicker'
import apiClient from '../api/client'
import { useSessions, useRevokeSession } from '../hooks/useSessions'

type Section = 'profile' | 'security' | 'sessions' | 'language' | 'notifications'

/**
 * User settings page.
 * Sections: Profile, Security, Language, Notifications (DND).
 */
export default function SettingsPage() {
  const { t } = useTranslation()
  const [section, setSection] = useState<Section>('profile')

  const nav: { key: Section; label: string; icon: React.ElementType }[] = [
    { key: 'profile', label: t('settings.profile', 'Profile'), icon: PersonRegular },
    { key: 'security', label: t('settings.security', 'Security'), icon: LockClosedRegular },
    { key: 'sessions', label: t('settings.sessions', '활성 세션'), icon: LaptopRegular },
    { key: 'language', label: t('settings.language', 'Language'), icon: GlobeRegular },
    { key: 'notifications', label: t('settings.notifications', 'Notifications'), icon: AlertBadgeRegular },
  ]

  return (
    <div className="px-6 py-8 max-w-3xl mx-auto">
      <h1 className="text-xl font-semibold text-text-primary tracking-tight mb-6">
        {t('nav.settings')}
      </h1>

      <div className="flex gap-6">
        {/* Sidebar nav */}
        <nav className="w-40 flex-shrink-0">
          <ul className="space-y-0.5">
            {nav.map(({ key, label, icon: Icon }) => (
              <li key={key}>
                <button
                  type="button"
                  onClick={() => setSection(key)}
                  className={[
                    'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors duration-75',
                    section === key
                      ? 'bg-bg-tertiary text-text-primary'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover',
                  ].join(' ')}
                >
                  <Icon style={{ fontSize: 15 }} />
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {section === 'profile' && <ProfileSection />}
          {section === 'security' && <SecuritySection />}
          {section === 'sessions' && <SessionsSection />}
          {section === 'language' && <LanguageSection />}
          {section === 'notifications' && <NotificationsSection />}
        </div>
      </div>
    </div>
  )
}

// ── Profile ───────────────────────────────────────────────────────────────────

function ProfileSection() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const [name, setName] = useState(user?.name ?? '')
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: async () => {
      // TODO: wire to PATCH /users/me
      await new Promise((r) => setTimeout(r, 400))
    },
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    mutation.mutate()
  }

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('settings.profile', 'Profile')}
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Avatar placeholder */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-14 h-14 rounded-full bg-bg-tertiary border border-border flex items-center justify-center">
            <span className="text-lg font-bold text-text-secondary font-mono">
              {(user?.name ?? 'U')[0].toUpperCase()}
            </span>
          </div>
          <div>
            <p className="text-sm text-text-primary">{user?.name}</p>
            <p className="text-xs text-text-tertiary font-mono">{user?.email}</p>
          </div>
        </div>

        <Field label={t('settings.displayName', 'Display name')}>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full h-9 px-3 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all duration-150"
          />
        </Field>

        <Field label={t('auth.email')}>
          <input
            type="email"
            value={user?.email ?? ''}
            disabled
            className="w-full h-9 px-3 rounded-lg bg-bg-tertiary border border-border text-text-tertiary text-sm cursor-not-allowed opacity-60"
          />
        </Field>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="h-8 px-4 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors duration-100 disabled:opacity-50"
          >
            {mutation.isPending ? t('common.loading') : t('common.save')}
          </button>
          {saved && (
            <span className="inline-flex items-center gap-1 text-success text-xs font-mono">
              <CheckmarkRegular style={{ fontSize: 13 }} />
              {t('settings.saved', 'Saved')}
            </span>
          )}
        </div>
      </form>
    </div>
  )
}

// ── Security ──────────────────────────────────────────────────────────────────

function SecuritySection() {
  const { t } = useTranslation()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('settings.security', 'Security')}
      </h2>

      <form
        onSubmit={(e) => e.preventDefault()}
        className="space-y-4"
      >
        <Field label={t('settings.currentPassword', 'Current password')}>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            className="w-full h-9 px-3 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all duration-150"
          />
        </Field>

        <Field label={t('settings.newPassword', 'New password')}>
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            className="w-full h-9 px-3 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all duration-150"
          />
        </Field>

        <div className="pt-2">
          <button
            type="submit"
            className="h-8 px-4 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors duration-100 opacity-50 cursor-not-allowed"
            disabled
            title="Coming soon"
          >
            {t('settings.changePassword', 'Change password')}
          </button>
        </div>
      </form>

      {/* ── Passkey / 2FA stubs ──────────────────────────────────────── */}
      <div className="mt-8 border-t border-border pt-6 space-y-4">
        <h3 className="text-xs font-mono text-text-tertiary uppercase tracking-wider mb-4">
          {t('settings.advancedSecurity', '고급 보안')}
        </h3>

        {/* Passkey */}
        <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-bg-tertiary border border-border">
          <div className="flex items-center gap-3">
            <KeyRegular style={{ fontSize: 18 }} className="text-text-secondary flex-shrink-0" />
            <div>
              <p className="text-sm text-text-primary">Passkey</p>
              <p className="text-xs text-text-tertiary mt-0.5">
                {t('settings.passkeyDesc', '비밀번호 없이 생체인식 또는 보안 키로 로그인')}
              </p>
            </div>
          </div>
          <div title="Coming soon">
            <button
              type="button"
              disabled
              className="h-8 px-3 rounded-lg bg-bg-hover border border-border text-text-tertiary text-xs font-medium opacity-50 cursor-not-allowed"
            >
              {t('settings.register', '등록')}
            </button>
          </div>
        </div>

        {/* 2FA TOTP */}
        <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-bg-tertiary border border-border">
          <div className="flex items-center gap-3">
            <ShieldLockRegular style={{ fontSize: 18 }} className="text-text-secondary flex-shrink-0" />
            <div>
              <p className="text-sm text-text-primary">2FA (TOTP)</p>
              <p className="text-xs text-text-tertiary mt-0.5">
                {t('settings.totpDesc', 'Google Authenticator 등 앱으로 2단계 인증 설정')}
              </p>
            </div>
          </div>
          <div title="Coming soon">
            <button
              type="button"
              disabled
              className="h-8 px-3 rounded-lg bg-bg-hover border border-border text-text-tertiary text-xs font-medium opacity-50 cursor-not-allowed"
            >
              {t('settings.setup', '설정')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Sessions ──────────────────────────────────────────────────────────────────

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
function SessionsSection() {
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

// ── Language ──────────────────────────────────────────────────────────────────

const LANGS = [
  { code: 'ko', label: '한국어' },
  { code: 'en', label: 'English' },
]

function LanguageSection() {
  const { t, i18n: _i18n } = useTranslation()
  const [current, setCurrent] = useState(i18n.language)

  function changeLang(code: string) {
    i18n.changeLanguage(code)
    setCurrent(code)
    localStorage.setItem('jongji-lang', code)
  }

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('settings.language', 'Language')}
      </h2>

      <div className="space-y-2">
        {LANGS.map(({ code, label }) => (
          <button
            key={code}
            type="button"
            onClick={() => changeLang(code)}
            className={[
              'w-full flex items-center justify-between px-4 py-3 rounded-lg border text-sm transition-all duration-100',
              current === code
                ? 'border-accent/60 bg-accent/10 text-text-primary'
                : 'border-border bg-bg-tertiary text-text-secondary hover:bg-bg-hover hover:text-text-primary',
            ].join(' ')}
          >
            {label}
            {current === code && (
              <CheckmarkRegular className="text-accent" style={{ fontSize: 15 }} />
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Notifications (DND) ───────────────────────────────────────────────────────

/** Convert "HH:mm" to fractional hours (0–24). */
function timeToHours(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return (h ?? 0) + (m ?? 0) / 60
}

/** Format "HH:mm" to a locale-friendly display string. */
function formatTime(t: string): string {
  const [h, m] = t.split(':')
  const date = new Date()
  date.setHours(Number(h), Number(m), 0, 0)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

interface DndTimelineProps {
  startTime: string
  endTime: string
  enabled: boolean
}

/**
 * Visual 24h timeline bar showing the DND window.
 * Wraps around midnight correctly.
 */
function DndTimeline({ startTime, endTime, enabled }: DndTimelineProps) {
  const { t } = useTranslation()
  const startH = timeToHours(startTime)
  const endH = timeToHours(endTime)

  // Compute left% and width% on the 0-24h bar
  let leftPct: number
  let widthPct: number

  if (startH < endH) {
    // Same-day range, e.g. 09:00 → 17:00
    leftPct = (startH / 24) * 100
    widthPct = ((endH - startH) / 24) * 100
  } else if (startH > endH) {
    // Overnight range, e.g. 22:00 → 07:00 — show as two segments
    // We approximate by showing from startH to midnight (wrapped)
    leftPct = (startH / 24) * 100
    widthPct = ((24 - startH + endH) / 24) * 100
  } else {
    // Same time = full 24h or 0
    leftPct = 0
    widthPct = 100
  }

  // Hour ticks: 0, 6, 12, 18, 24
  const ticks = [0, 6, 12, 18, 24]

  return (
    <div
      aria-label={t('settings.dnd.timelineLabel', '24h timeline')}
      className="mt-5"
    >
      <p className="text-xs font-mono text-text-tertiary uppercase tracking-wider mb-2">
        {t('settings.dnd.timelineLabel', '24h timeline')}
      </p>

      {/* Track */}
      <div className="relative h-5 rounded-full bg-bg-tertiary border border-border overflow-hidden">
        {/* DND window */}
        {enabled && (
          <div
            className="absolute top-0 h-full rounded-full transition-all duration-300"
            style={{
              left: `${leftPct}%`,
              width: `${Math.min(widthPct, 100 - leftPct)}%`,
              backgroundColor: 'var(--color-accent)',
              opacity: 0.55,
            }}
          />
        )}
        {/* Overnight overflow segment */}
        {enabled && startH > endH && (
          <div
            className="absolute top-0 h-full rounded-full transition-all duration-300"
            style={{
              left: 0,
              width: `${(endH / 24) * 100}%`,
              backgroundColor: 'var(--color-accent)',
              opacity: 0.55,
            }}
          />
        )}
      </div>

      {/* Tick labels */}
      <div className="flex justify-between mt-1 px-0.5">
        {ticks.map((h) => (
          <span key={h} className="text-[10px] font-mono text-text-tertiary">
            {String(h % 24).padStart(2, '0')}
          </span>
        ))}
      </div>

      {/* Legend */}
      {enabled && (
        <p className="mt-2 text-xs text-text-tertiary font-mono">
          {formatTime(startTime)} → {formatTime(endTime)}
        </p>
      )}
    </div>
  )
}

interface DndUserProfile {
  dnd_start: string | null
  dnd_end: string | null
}

/**
 * Mock GET /api/v1/users/me for DND fields.
 * Returns null until the backend endpoint exists.
 */
async function fetchDndProfile(): Promise<DndUserProfile> {
  try {
    const res = await apiClient.get<DndUserProfile>('/users/me')
    return res.data
  } catch {
    // Backend not yet available — return defaults
    return { dnd_start: null, dnd_end: null }
  }
}

/**
 * PUT /api/v1/users/me to persist DND times.
 */
async function saveDndProfile(data: DndUserProfile): Promise<void> {
  await apiClient.put('/users/me', data)
}

function NotificationsSection() {
  const { t } = useTranslation()
  const [enabled, setEnabled] = useState(false)
  const [startTime, setStartTime] = useState('22:00')
  const [endTime, setEndTime] = useState('07:00')
  const [saved, setSaved] = useState(false)
  const [loadError, setLoadError] = useState(false)

  // Load current DND settings on mount
  useState(() => {
    fetchDndProfile()
      .then((profile) => {
        if (profile.dnd_start && profile.dnd_end) {
          setEnabled(true)
          setStartTime(profile.dnd_start)
          setEndTime(profile.dnd_end)
        }
      })
      .catch(() => setLoadError(true))
  })

  const mutation = useMutation({
    mutationFn: () =>
      saveDndProfile({
        dnd_start: enabled ? startTime : null,
        dnd_end: enabled ? endTime : null,
      }),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  // Determine if currently in DND window (for status indicator)
  function isCurrentlyInDnd(): boolean {
    if (!enabled) return false
    const now = new Date()
    const currentH = now.getHours() + now.getMinutes() / 60
    const startH = timeToHours(startTime)
    const endH = timeToHours(endTime)
    if (startH < endH) return currentH >= startH && currentH < endH
    return currentH >= startH || currentH < endH
  }

  const inDnd = isCurrentlyInDnd()

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-1">
        {t('settings.notifications', 'Notification Settings')}
      </h2>
      <p className="text-xs text-text-tertiary mb-5">
        {t('settings.dnd.description', 'Silence all notifications during the specified time window.')}
      </p>

      {/* Status badge */}
      <div
        className={[
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono mb-5 border transition-colors duration-200',
          inDnd
            ? 'border-accent/40 bg-accent/10 text-accent'
            : 'border-border bg-bg-tertiary text-text-tertiary',
        ].join(' ')}
      >
        <span
          className={[
            'w-1.5 h-1.5 rounded-full',
            inDnd ? 'bg-accent animate-pulse' : 'bg-text-tertiary',
          ].join(' ')}
        />
        {inDnd
          ? t('settings.dnd.activeStatus', 'Do Not Disturb is on')
          : t('settings.dnd.inactiveStatus', 'Do Not Disturb is off')}
      </div>

      {loadError && (
        <p className="text-xs text-warning mb-4 font-mono">
          Could not load saved settings. Using defaults.
        </p>
      )}

      {/* DND toggle */}
      <div className="flex items-center justify-between py-3 border-b border-border">
        <div>
          <p className="text-sm text-text-primary">
            {t('settings.dnd.title', 'Do Not Disturb')}
          </p>
          <p className="text-xs text-text-tertiary mt-0.5">
            {t('settings.dnd.enable', 'Enable Do Not Disturb')}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          onClick={() => setEnabled((v) => !v)}
          className={[
            'relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent',
            'transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-accent/40 focus:ring-offset-1 focus:ring-offset-bg-primary',
            enabled ? 'bg-accent' : 'bg-bg-hover',
          ].join(' ')}
        >
          <span className="sr-only">{t('settings.dnd.enable', 'Enable Do Not Disturb')}</span>
          <span
            className={[
              'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm',
              'transition-transform duration-200',
              enabled ? 'translate-x-4' : 'translate-x-0',
            ].join(' ')}
          />
        </button>
      </div>

      {/* Time pickers — fade in when enabled */}
      <div
        className={[
          'transition-all duration-200 overflow-hidden',
          enabled ? 'opacity-100 max-h-96 mt-5' : 'opacity-0 max-h-0 pointer-events-none',
        ].join(' ')}
        aria-hidden={!enabled}
      >
        <div className="flex items-end gap-6">
          <TimePicker
            label={t('settings.dnd.startTime', 'Start time')}
            value={startTime}
            onChange={setStartTime}
            disabled={!enabled}
          />
          <span className="text-text-tertiary text-sm pb-1 font-mono select-none">→</span>
          <TimePicker
            label={t('settings.dnd.endTime', 'End time')}
            value={endTime}
            onChange={setEndTime}
            disabled={!enabled}
          />
        </div>

        <DndTimeline startTime={startTime} endTime={endTime} enabled={enabled} />
      </div>

      {/* Save button */}
      <div className="flex items-center gap-3 mt-6">
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="h-8 px-4 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors duration-100 disabled:opacity-50"
        >
          {mutation.isPending
            ? t('common.loading')
            : t('settings.dnd.save', 'Save')}
        </button>
        {saved && (
          <span className="inline-flex items-center gap-1 text-success text-xs font-mono">
            <CheckmarkRegular style={{ fontSize: 13 }} />
            {t('settings.saved', 'Saved')}
          </span>
        )}
        {mutation.isError && (
          <span className="text-danger text-xs font-mono">
            Failed to save. Please try again.
          </span>
        )}
      </div>
    </div>
  )
}

// ── Field ─────────────────────────────────────────────────────────────────────

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-mono text-text-tertiary uppercase tracking-wider">
        {label}
      </label>
      {children}
    </div>
  )
}
