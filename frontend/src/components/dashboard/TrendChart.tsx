/**
 * TrendChart — area chart showing daily created/completed task trend.
 */
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { DashboardTooltip } from './DashboardTooltip'
import { EmptyChart } from './ChartCard'

interface TrendChartProps {
  created: { date: string; count: number }[]
  completed: { date: string; count: number }[]
}

export function TrendChart({ created, completed }: TrendChartProps) {
  if (!created.length && !completed.length) return <EmptyChart />

  // Merge by date
  const dateMap: Record<string, { date: string; created: number; completed: number }> = {}
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
        <Tooltip content={<DashboardTooltip />} />
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
