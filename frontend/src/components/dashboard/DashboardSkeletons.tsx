/**
 * DashboardSkeletons — loading skeleton components for dashboard cards/charts.
 */

export function CardSkeleton() {
  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-5 animate-pulse">
      <div className="h-3 w-24 bg-bg-tertiary rounded mb-4" />
      <div className="h-8 w-16 bg-bg-tertiary rounded mb-2" />
      <div className="h-2 w-32 bg-bg-tertiary rounded" />
    </div>
  )
}

export function ChartSkeleton() {
  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-5 animate-pulse">
      <div className="h-3 w-32 bg-bg-tertiary rounded mb-6" />
      <div className="h-48 bg-bg-tertiary rounded-lg" />
    </div>
  )
}
