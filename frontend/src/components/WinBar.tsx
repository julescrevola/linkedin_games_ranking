interface WinBarProps {
  w1: number
  w2: number
  color1: string
  color2: string
  label?: string
  height?: number
}

export default function WinBar({ w1, w2, color1, color2, label, height = 24 }: WinBarProps) {
  const total = w1 + w2
  if (total === 0) return null
  const p1Pct = (w1 / total) * 100
  const p2Pct = (w2 / total) * 100

  return (
    <div className="mb-1">
      {label && <p className="text-sm text-gray-400 mb-1 font-medium">{label}</p>}
      <div className="flex items-center gap-2">
        <span className="min-w-[28px] text-right text-sm font-semibold" style={{ color: color1 }}>
          {w1}
        </span>
        <div className="flex flex-1 rounded overflow-hidden" style={{ height }}>
          <div style={{ width: `${p1Pct}%`, backgroundColor: color1, minWidth: w1 > 0 ? 2 : 0 }} />
          <div style={{ width: `${p2Pct}%`, backgroundColor: color2, minWidth: w2 > 0 ? 2 : 0 }} />
        </div>
        <span className="min-w-[28px] text-left text-sm font-semibold" style={{ color: color2 }}>
          {w2}
        </span>
      </div>
    </div>
  )
}
