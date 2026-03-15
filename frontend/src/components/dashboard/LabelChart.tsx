/**
 * LabelChart — donut pie chart showing label distribution.
 */
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts'
import { CHART_COLORS } from '../../constants/task'
import { DashboardTooltip } from './DashboardTooltip'
import { EmptyChart } from './ChartCard'

interface LabelChartProps {
  labels: { label_id: string; label_name: string; color: string; count: number }[]
}

export function LabelChart({ labels }: LabelChartProps) {
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
          <Tooltip content={<DashboardTooltip />} />
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
