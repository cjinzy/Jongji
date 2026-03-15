/**
 * Dashboard page showing project analytics:
 * KPI cards, status/label pie charts, daily trend area chart,
 * priority and assignee workload bar charts.
 */
import { useTranslation } from 'react-i18next'
import {
  DataHistogramRegular,
  ArrowSyncRegular,
  CheckmarkCircleRegular,
  TasksAppRegular,
  ClockRegular,
  PersonRegular,
} from '@fluentui/react-icons'
import { useDashboard } from '../hooks/useDashboard'
import { useResolvedProjectId } from '../hooks/useResolvedProjectId'
import { CardSkeleton, ChartSkeleton } from '../components/dashboard/DashboardSkeletons'
import { KpiCard } from '../components/dashboard/KpiCard'
import { ChartCard } from '../components/dashboard/ChartCard'
import { StatusPie } from '../components/dashboard/StatusPie'
import { TrendChart } from '../components/dashboard/TrendChart'
import { PriorityChart } from '../components/dashboard/PriorityChart'
import { WorkloadChart } from '../components/dashboard/WorkloadChart'
import { LabelChart } from '../components/dashboard/LabelChart'

export default function DashboardPage() {
  const { projectId } = useResolvedProjectId()
  const { t } = useTranslation()
  const { data, isLoading, error, refetch, isFetching } = useDashboard(projectId)

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between mb-2">
          <div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <ChartSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Error state
  // ---------------------------------------------------------------------------
  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
        <div className="w-12 h-12 rounded-xl bg-bg-tertiary border border-border flex items-center justify-center">
          <DataHistogramRegular className="text-text-tertiary" style={{ fontSize: 22 }} />
        </div>
        <div>
          <p className="text-sm font-medium text-text-primary mb-1">
            {t('nav.dashboard')}
          </p>
          <p className="text-xs text-text-tertiary font-mono">
            {error ? 'Failed to load dashboard data' : t('common.comingSoon', 'Coming soon')}
          </p>
        </div>
        {error && (
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover transition-colors"
          >
            <ArrowSyncRegular style={{ fontSize: 14 }} />
            Retry
          </button>
        )}
      </div>
    )
  }

  const inProgressCount =
    (data.status_counts['PROGRESS'] ?? 0) + (data.status_counts['REVIEW'] ?? 0)

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="p-6 space-y-6 min-h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-sm font-semibold text-text-primary">
            {t('nav.dashboard')}
          </h1>
          <p className="text-xs text-text-tertiary mt-0.5">
            Project overview &amp; analytics
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 text-xs text-text-tertiary hover:text-text-primary transition-colors disabled:opacity-50"
          aria-label="Refresh dashboard"
        >
          <ArrowSyncRegular
            style={{ fontSize: 14 }}
            className={isFetching ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard
          label="Total Tasks"
          value={data.total_tasks}
          icon={<TasksAppRegular />}
          accent="#5B6AF0"
        />
        <KpiCard
          label="Completed"
          value={data.completed_tasks}
          icon={<CheckmarkCircleRegular />}
          accent="#22C55E"
        />
        <KpiCard
          label="Completion Rate"
          value={`${Math.round(data.completion_rate * 100)}%`}
          sub={`${data.completed_tasks} of ${data.total_tasks}`}
          icon={<DataHistogramRegular />}
          accent="#8B5CF6"
        />
        <KpiCard
          label="In Progress"
          value={inProgressCount}
          sub="Progress + Review"
          icon={<ClockRegular />}
          accent="#F59E0B"
        />
      </div>

      {/* Chart grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Status Distribution */}
        <ChartCard title="Status Distribution">
          <StatusPie statusCounts={data.status_counts} />
        </ChartCard>

        {/* Daily Trend */}
        <ChartCard title="Daily Trend (30 days)">
          <TrendChart
            created={data.daily_created}
            completed={data.daily_completed}
          />
          {/* Legend */}
          <div className="flex items-center gap-4 mt-3">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-accent inline-block rounded" />
              <span className="text-xs text-text-tertiary">Created</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-success inline-block rounded" />
              <span className="text-xs text-text-tertiary">Completed</span>
            </div>
          </div>
        </ChartCard>

        {/* Priority Distribution */}
        <ChartCard title="Priority Distribution">
          <PriorityChart distribution={data.priority_distribution} />
        </ChartCard>

        {/* Assignee Workload */}
        <ChartCard title="Assignee Workload">
          {data.assignee_workload.length ? (
            <WorkloadChart workload={data.assignee_workload} />
          ) : (
            <div className="h-48 flex items-center justify-center gap-2 text-xs text-text-tertiary">
              <PersonRegular style={{ fontSize: 16 }} />
              No assignee data
            </div>
          )}
        </ChartCard>

        {/* Label Distribution */}
        <ChartCard title="Label Distribution">
          <LabelChart labels={data.label_distribution} />
        </ChartCard>
      </div>
    </div>
  )
}
