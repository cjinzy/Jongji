/**
 * KpiCard — key performance indicator card for the dashboard.
 */

interface KpiCardProps {
  label: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  accent?: string
}

export function KpiCard({ label, value, sub, icon, accent = '#5B6AF0' }: KpiCardProps) {
  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-5 flex items-start gap-4 hover:border-accent/30 transition-colors">
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: `${accent}18` }}
      >
        <span style={{ color: accent, fontSize: 18 }}>{icon}</span>
      </div>
      <div className="min-w-0">
        <p className="text-xs text-text-tertiary mb-0.5 font-medium tracking-wide uppercase">
          {label}
        </p>
        <p className="text-2xl font-semibold text-text-primary leading-none mb-1">
          {value}
        </p>
        {sub && <p className="text-xs text-text-tertiary">{sub}</p>}
      </div>
    </div>
  )
}
