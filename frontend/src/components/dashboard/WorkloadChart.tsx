/**
 * WorkloadChart — horizontal bar chart showing assignee workload distribution.
 */
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
} from 'recharts'
import { DashboardTooltip } from './DashboardTooltip'
import { EmptyChart } from './ChartCard'

interface WorkloadChartProps {
  workload: { user_id: string; user_name: string; count: number }[]
}

export function WorkloadChart({ workload }: WorkloadChartProps) {
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
        <Tooltip content={<DashboardTooltip />} />
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
