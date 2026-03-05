import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import { CheckmarkRegular } from '@fluentui/react-icons'
import TimePicker from '../../components/TimePicker'
import apiClient from '../../api/client'

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

/**
 * Notifications / Do Not Disturb settings section.
 */
export default function NotificationsSection() {
  const { t } = useTranslation()
  const [enabled, setEnabled] = useState(false)
  const [startTime, setStartTime] = useState('22:00')
  const [endTime, setEndTime] = useState('07:00')
  const [saved, setSaved] = useState(false)
  const [loadError, setLoadError] = useState(false)

  // Load current DND settings on mount
  useEffect(() => {
    fetchDndProfile()
      .then((profile) => {
        if (profile.dnd_start && profile.dnd_end) {
          setEnabled(true)
          setStartTime(profile.dnd_start)
          setEndTime(profile.dnd_end)
        }
      })
      .catch(() => setLoadError(true))
  }, [])

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
