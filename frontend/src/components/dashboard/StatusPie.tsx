/**
 * StatusPie — donut pie chart showing task status distribution.
 */
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts'
import { STATUS_LABELS, STATUS_COLORS } from '../../constants/task'
import { DashboardTooltip } from './DashboardTooltip'
import { EmptyChart } from './ChartCard'

interface StatusPieProps {
  statusCounts: Record<string, number>
}

export function StatusPie({ statusCounts }: StatusPieProps) {
  const data = Object.entries(statusCounts)
    .filter(([, v]) => v > 0)
    .map(([key, value]) => ({
      name: STATUS_LABELS[key as keyof typeof STATUS_LABELS] ?? key,
      value,
      color: STATUS_COLORS[key as keyof typeof STATUS_COLORS] ?? '#6B6B76',
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
          <Tooltip content={<DashboardTooltip />} />
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
