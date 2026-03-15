/**
 * DashboardTooltip — dark-themed recharts tooltip for dashboard charts.
 */

export interface TooltipPayloadItem {
  name: string
  value: number
  color?: string
}

interface DashboardTooltipProps {
  active?: boolean
  payload?: TooltipPayloadItem[]
  label?: string
}

export function DashboardTooltip({ active, payload, label }: DashboardTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div
      style={{
        background: 'var(--color-bg-secondary)',
        border: '1px solid var(--color-border)',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 12,
        color: 'var(--color-text-primary)',
      }}
    >
      {label && (
        <p
          style={{
            color: 'var(--color-text-secondary)',
            marginBottom: 4,
            fontWeight: 500,
          }}
        >
          {label}
        </p>
      )}
      {payload.map((entry) => (
        <div
          key={entry.name}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: entry.color,
              display: 'inline-block',
              flexShrink: 0,
            }}
          />
          <span style={{ color: 'var(--color-text-secondary)' }}>
            {entry.name}:
          </span>
          <span style={{ fontWeight: 600 }}>{entry.value}</span>
        </div>
      ))}
    </div>
  )
}
