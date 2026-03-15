/**
 * ChartCard — wrapper card with title for dashboard chart sections.
 */

interface ChartCardProps {
  title: string
  children: React.ReactNode
}

export function ChartCard({ title, children }: ChartCardProps) {
  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-5">
      <p className="text-xs text-text-tertiary font-medium uppercase tracking-wide mb-5">
        {title}
      </p>
      {children}
    </div>
  )
}

export function EmptyChart() {
  return (
    <div className="h-48 flex items-center justify-center">
      <p className="text-xs text-text-tertiary">No data available</p>
    </div>
  )
}
