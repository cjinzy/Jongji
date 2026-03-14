import { useTranslation } from 'react-i18next'
import {
  DataHistogramRegular,
  ArrowSyncRegular,
  CheckmarkCircleRegular,
  TasksAppRegular,
  ClockRegular,
  PersonRegular,
} from '@fluentui/react-icons'
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
  LabelList,
} from 'recharts'
import { useDashboard } from '../hooks/useDashboard'
import { useResolvedProjectId } from '../hooks/useResolvedProjectId'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const STATUS_COLORS: Record<string, string> = {
  BACKLOG: '#6B6B76',
  TODO: '#5B6AF0',
  PROGRESS: '#F59E0B',
  REVIEW: '#8B5CF6',
  DONE: '#22C55E',
  REOPEN: '#EF4444',
  CLOSED: '#374151',
}

const STATUS_LABELS: Record<string, string> = {
  BACKLOG: 'Backlog',
  TODO: 'Todo',
  PROGRESS: 'In Progress',
  REVIEW: 'In Review',
  DONE: 'Done',
  REOPEN: 'Reopened',
  CLOSED: 'Closed',
}

const PRIORITY_LABELS: Record<number, string> = {
  0: 'None',
  1: 'Low',
  2: 'Medium',
  3: 'High',
  4: 'Urgent',
}

const PRIORITY_COLORS: Record<number, string> = {
  0: '#6B7280',
  1: '#5B6AF0',
  2: '#F59E0B',
  3: '#F97316',
  4: '#EF4444',
}

const CHART_COLORS = [
  '#5B6AF0',
  '#22C55E',
  '#F59E0B',
  '#8B5CF6',
  '#EF4444',
  '#06B6D4',
  '#EC4899',
  '#F97316',
]

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------
interface TooltipProps {
  active?: boolean
  payload?: { name: string; value: number; color?: string }[]
  label?: string
}

function DarkTooltip({ active, payload, label }: TooltipProps) {
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

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------
function CardSkeleton() {
  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-5 animate-pulse">
      <div className="h-3 w-24 bg-bg-tertiary rounded mb-4" />
      <div className="h-8 w-16 bg-bg-tertiary rounded mb-2" />
      <div className="h-2 w-32 bg-bg-tertiary rounded" />
    </div>
  )
}

function ChartSkeleton() {
  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-5 animate-pulse">
      <div className="h-3 w-32 bg-bg-tertiary rounded mb-6" />
      <div className="h-48 bg-bg-tertiary rounded-lg" />
    </div>
  )
}

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------
interface KpiCardProps {
  label: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  accent?: string
}

function KpiCard({ label, value, sub, icon, accent = '#5B6AF0' }: KpiCardProps) {
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

// ---------------------------------------------------------------------------
// Chart card wrapper
// ---------------------------------------------------------------------------
function ChartCard({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-5">
      <p className="text-xs text-text-tertiary font-medium uppercase tracking-wide mb-5">
        {title}
      </p>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------
function EmptyChart() {
  return (
    <div className="h-48 flex items-center justify-center">
      <p className="text-xs text-text-tertiary">No data available</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Status Distribution Pie
// ---------------------------------------------------------------------------
interface StatusPieProps {
  statusCounts: Record<string, number>
}

function StatusPie({ statusCounts }: StatusPieProps) {
  const data = Object.entries(statusCounts)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: STATUS_LABELS[key] ?? key,
      value,
      color: STATUS_COLORS[key] ?? '#6B6B76',
    }))

  if (!data.length) return <EmptyChart />

  return (
    <div className="flex items-center gap-6">
      <ResponsiveContainer width={160} height={160}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={46}
            outerRadius={70}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} stroke="transparent" />
            ))}
          </Pie>
          <Tooltip content={<DarkTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="flex-1 space-y-2">
        {data.map((entry) => (
          <li key={entry.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ background: entry.color }}
              />
              <span className="text-xs text-text-secondary">{entry.name}</span>
            </div>
            <span className="text-xs font-semibold text-text-primary tabular-nums">
              {entry.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Daily Trend Area Chart
// ---------------------------------------------------------------------------
interface TrendChartProps {
  created: { date: string; count: number }[]
  completed: { date: string; count: number }[]
}

function TrendChart({ created, completed }: TrendChartProps) {
  if (!created.length && !completed.length) return <EmptyChart />

  // Merge by date
  const dateMap: Record<string, { date: string; created: number; completed: number }> =
    {}
  created.forEach(({ date, count }) => {
    dateMap[date] = { date, created: count, completed: 0 }
  })
  completed.forEach(({ date, count }) => {
    if (dateMap[date]) dateMap[date].completed = count
    else dateMap[date] = { date, created: 0, completed: count }
  })

  const data = Object.values(dateMap)
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => ({ ...d, date: d.date.slice(5) })) // MM-DD

  return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <defs>
          <linearGradient id="gradCreated" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#5B6AF0" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#5B6AF0" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradCompleted" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22C55E" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#22C55E" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2E" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: '#6B6B76', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: '#6B6B76', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <Tooltip content={<DarkTooltip />} />
        <Area
          type="monotone"
          dataKey="created"
          name="Created"
          stroke="#5B6AF0"
          strokeWidth={2}
          fill="url(#gradCreated)"
          dot={false}
        />
        <Area
          type="monotone"
          dataKey="completed"
          name="Completed"
          stroke="#22C55E"
          strokeWidth={2}
          fill="url(#gradCompleted)"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// ---------------------------------------------------------------------------
// Priority Bar Chart (horizontal)
// ---------------------------------------------------------------------------
interface PriorityChartProps {
  distribution: { priority: number; count: number }[]
}

function PriorityChart({ distribution }: PriorityChartProps) {
  if (!distribution.length) return <EmptyChart />

  const data = distribution
    .filter((d) => d.count > 0)
    .map((d) => ({
      name: PRIORITY_LABELS[d.priority] ?? `P${d.priority}`,
      count: d.count,
      color: PRIORITY_COLORS[d.priority] ?? '#6B7280',
    }))

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 36)}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 0, right: 40, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2E" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: '#6B6B76', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fill: '#A0A0A8', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={96}
        />
        <Tooltip content={<DarkTooltip />} />
        <Bar dataKey="count" name="Tasks" radius={[0, 4, 4, 0]} maxBarSize={18}>
          {data.map((entry) => (
            <Cell key={entry.name} fill={entry.color} />
          ))}
          <LabelList
            dataKey="count"
            position="right"
            style={{ fill: '#A0A0A8', fontSize: 11, fontWeight: 600 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ---------------------------------------------------------------------------
// Assignee Workload Bar Chart (horizontal)
// ---------------------------------------------------------------------------
interface WorkloadChartProps {
  workload: { user_id: string; user_name: string; count: number }[]
}

function WorkloadChart({ workload }: WorkloadChartProps) {
  if (!workload.length) return <EmptyChart />

  const data = workload
    .slice(0, 10)
    .sort((a, b) => b.count - a.count)
    .map((d) => ({ name: d.user_name, count: d.count }))

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 36)}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 0, right: 40, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2E" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: '#6B6B76', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fill: '#A0A0A8', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={96}
        />
        <Tooltip content={<DarkTooltip />} />
        <Bar
          dataKey="count"
          name="Tasks"
          fill="#5B6AF0"
          radius={[0, 4, 4, 0]}
          maxBarSize={18}
        >
          <LabelList
            dataKey="count"
            position="right"
            style={{ fill: '#A0A0A8', fontSize: 11, fontWeight: 600 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ---------------------------------------------------------------------------
// Label Distribution Pie
// ---------------------------------------------------------------------------
interface LabelChartProps {
  labels: { label_id: string; label_name: string; color: string; count: number }[]
}

function LabelChart({ labels }: LabelChartProps) {
  if (!labels.length) return <EmptyChart />

  const data = labels
    .filter((l) => l.count > 0)
    .map((l, i) => ({
      name: l.label_name,
      value: l.count,
      color: l.color || CHART_COLORS[i % CHART_COLORS.length],
    }))

  return (
    <div className="flex items-center gap-6">
      <ResponsiveContainer width={160} height={160}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={46}
            outerRadius={70}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} stroke="transparent" />
            ))}
          </Pie>
          <Tooltip content={<DarkTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="flex-1 space-y-2 max-h-40 overflow-y-auto">
        {data.map((entry) => (
          <li key={entry.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ background: entry.color }}
              />
              <span className="text-xs text-text-secondary truncate max-w-[100px]">
                {entry.name}
              </span>
            </div>
            <span className="text-xs font-semibold text-text-primary tabular-nums">
              {entry.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

/**
 * Dashboard page showing project analytics:
 * KPI cards, status/label pie charts, daily trend area chart,
 * priority and assignee workload bar charts.
 */
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

  const inProgressCount = (data.status_counts['PROGRESS'] ?? 0) +
    (data.status_counts['REVIEW'] ?? 0)

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
