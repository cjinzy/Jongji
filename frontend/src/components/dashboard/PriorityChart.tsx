/**
 * PriorityChart — horizontal bar chart showing task priority distribution.
 */
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  LabelList,
} from 'recharts'
import { PRIORITY_LABELS, PRIORITY_COLORS } from '../../constants/task'
import type { TaskPriority } from '../../types/task'
import { DashboardTooltip } from './DashboardTooltip'
import { EmptyChart } from './ChartCard'

interface PriorityChartProps {
  distribution: { priority: number; count: number }[]
}

export function PriorityChart({ distribution }: PriorityChartProps) {
  if (!distribution.length) return <EmptyChart />

  const data = distribution
    .filter((d) => d.count > 0)
    .map((d) => ({
      name: PRIORITY_LABELS[d.priority as TaskPriority] ?? `P${d.priority}`,
      count: d.count,
      color: PRIORITY_COLORS[d.priority as TaskPriority] ?? '#6B7280',
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
        <Tooltip content={<DashboardTooltip />} />
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
