import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchPlayers, fetchDates, fetchHeadToHead } from '../api'
import WinBar from '../components/WinBar'
import WinOverTimeChart from '../components/WinOverTimeChart'

const GAME_EMOJI: Record<string, string> = {
  zip: '⚡',
  tango: '💃',
  queens: '👑',
  'mini sudoku': '🔢',
  patches: '🧩',
}

export default function HeadToHeadPage() {
  const [player1, setPlayer1] = useState('')
  const [player2, setPlayer2] = useState('')
  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)
  const [countMissing, setCountMissing] = useState(false)

  const { data: playersData } = useQuery({ queryKey: ['players'], queryFn: fetchPlayers })
  const { data: datesData } = useQuery({ queryKey: ['dates'], queryFn: fetchDates })
  const players = playersData?.players ?? []
  const dates = datesData?.dates ?? []

  // Auto-select first two players
  const p1 = player1 || players[0] || ''
  const p2 = player2 || players[1] || ''

  const { data: h2h, isLoading } = useQuery({
    queryKey: ['head-to-head', p1, p2, dateFrom, dateTo, countMissing],
    queryFn: () =>
      fetchHeadToHead({
        player1: p1,
        player2: p2,
        date_from: dateFrom,
        date_to: dateTo,
        count_missing: countMissing,
      }),
    enabled: !!p1 && !!p2 && p1 !== p2,
  })

  const P1_COLOR = '#4A90D9'
  const P2_COLOR = '#E74C3C'

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">1v1 Head-to-Head</h1>

      {/* Player selectors */}
      <div className="flex gap-4 mb-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Player 1</label>
          <select
            value={p1}
            onChange={(e) => setPlayer1(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            {players.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Player 2</label>
          <select
            value={p2}
            onChange={(e) => setPlayer2(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            {players.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>

      {p1 === p2 && <p className="text-yellow-400 mb-4">Select two different players.</p>}

      {/* Date range */}
      <div className="flex gap-4 mb-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">From</label>
          <select
            value={dateFrom ?? dates[dates.length - 1] ?? ''}
            onChange={(e) => setDateFrom(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            {dates.slice().reverse().map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">To</label>
          <select
            value={dateTo ?? dates[0] ?? ''}
            onChange={(e) => setDateTo(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            {dates.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Count missing toggle */}
      <label className="flex items-center gap-2 mb-6 cursor-pointer">
        <input
          type="checkbox"
          checked={countMissing}
          onChange={(e) => setCountMissing(e.target.checked)}
          className="w-4 h-4"
        />
        <span className="text-sm text-gray-300">
          Count missing scores as losses
        </span>
      </label>

      {isLoading && <p className="text-gray-400">Loading...</p>}

      {h2h && !h2h.error && (
        <div>
          {/* Overall Record */}
          <h2 className="text-xl font-semibold mb-3">Overall Record</h2>
          <div className="flex justify-between items-center mb-4">
            <div className="text-center">
              <p className="text-sm text-gray-400">{h2h.player1}</p>
              <p className="text-2xl font-bold" style={{ color: P1_COLOR }}>
                {h2h.p1_wins}{' '}
                <span className="text-lg">
                  ({h2h.p1_wins + h2h.p2_wins > 0
                    ? Math.round((h2h.p1_wins / (h2h.p1_wins + h2h.p2_wins)) * 100)
                    : 0}%)
                </span>
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">Draws</p>
              <p className="text-xl font-semibold text-gray-500">{h2h.draws}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">{h2h.player2}</p>
              <p className="text-2xl font-bold" style={{ color: P2_COLOR }}>
                {h2h.p2_wins}{' '}
                <span className="text-lg">
                  ({h2h.p1_wins + h2h.p2_wins > 0
                    ? Math.round((h2h.p2_wins / (h2h.p1_wins + h2h.p2_wins)) * 100)
                    : 0}%)
                </span>
              </p>
            </div>
          </div>

          <WinBar w1={h2h.p1_wins} w2={h2h.p2_wins} color1={P1_COLOR} color2={P2_COLOR} height={32} />
          <p className="text-xs text-gray-500 mt-1">{h2h.total} matchups compared</p>

          {/* Win % Over Time */}
          {h2h.win_over_time.length > 0 && (
            <section className="mt-8">
              <h2 className="text-xl font-semibold mb-3">Win % Over Time</h2>
              <WinOverTimeChart
                data={h2h.win_over_time}
                player1={h2h.player1}
                player2={h2h.player2}
                color1={P1_COLOR}
                color2={P2_COLOR}
              />
            </section>
          )}

          {/* Wins by Day of Week */}
          {h2h.wins_by_weekday.length > 0 && (
            <section className="mt-8">
              <h2 className="text-xl font-semibold mb-3">Wins by Day of Week</h2>
              <div className="space-y-2">
                {h2h.wins_by_weekday.map((d: { day: string; p1_wins: number; p2_wins: number }) => (
                  <WinBar
                    key={d.day}
                    label={d.day}
                    w1={d.p1_wins}
                    w2={d.p2_wins}
                    color1={P1_COLOR}
                    color2={P2_COLOR}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Wins by Game */}
          {h2h.wins_by_game.length > 0 && (
            <section className="mt-8">
              <h2 className="text-xl font-semibold mb-3">Wins by Game</h2>
              <div className="space-y-2">
                {h2h.wins_by_game.map((g: { game: string; p1_wins: number; p2_wins: number }) => (
                  <WinBar
                    key={g.game}
                    label={`${GAME_EMOJI[g.game.toLowerCase()] ?? '🎮'} ${g.game}`}
                    w1={g.p1_wins}
                    w2={g.p2_wins}
                    color1={P1_COLOR}
                    color2={P2_COLOR}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {h2h?.error && <p className="text-yellow-400">{h2h.error}</p>}
    </div>
  )
}
