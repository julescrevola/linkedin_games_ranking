import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface WinOverTimeChartProps {
  data: { date: string; p1_pct: number; p2_pct: number }[]
  player1: string
  player2: string
  color1: string
  color2: string
}

export default function WinOverTimeChart({ data, player1, player2, color1, color2 }: WinOverTimeChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} stackOffset="expand">
        <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} />
        <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fill: '#9ca3af', fontSize: 11 }} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
          labelStyle={{ color: '#d1d5db' }}
          formatter={(value: number, name: string) => [`${Math.round(value * 100)}%`, name]}
        />
        <Area
          type="monotone"
          dataKey="p1_pct"
          name={player1}
          stackId="1"
          stroke={color1}
          fill={color1}
          fillOpacity={0.8}
        />
        <Area
          type="monotone"
          dataKey="p2_pct"
          name={player2}
          stackId="1"
          stroke={color2}
          fill={color2}
          fillOpacity={0.8}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
