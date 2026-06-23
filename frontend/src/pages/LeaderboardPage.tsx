import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDates, fetchLeaderboard, uploadChat } from '../api'
import DataTable from '../components/DataTable'

const RANKING_TYPES_ALL = [
  'Total Points',
  'Total Time',
  'Average Time',
  'Times N°1',
  'Weekday Scores',
  'Times N°1 per Weekday',
]
const RANKING_TYPES_DAY = ['Total Points', 'Total Time', 'Average Time', 'Times N°1']

export default function LeaderboardPage() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [mode, setMode] = useState<'stored' | 'upload'>('stored')
  const [dayFilter, setDayFilter] = useState('All')
  const [dayFrom, setDayFrom] = useState<string | null>(null)
  const [dayTo, setDayTo] = useState<string | null>(null)
  const [rankingType, setRankingType] = useState('Total Points')

  // Fetch available dates
  const { data: datesData } = useQuery({
    queryKey: ['dates'],
    queryFn: fetchDates,
  })
  const dates = datesData?.dates ?? []

  // Default start date
  const defaultStart = '2026-06-01'
  const effectiveDayFrom = dayFilter === 'All' ? (dayFrom ?? defaultStart) : undefined
  const effectiveDayTo = dayFilter === 'All' ? (dayTo ?? dates[0] ?? undefined) : undefined

  // Fetch leaderboard data
  const { data: leaderboard, isLoading, error } = useQuery({
    queryKey: ['leaderboard', dayFilter, effectiveDayFrom, effectiveDayTo],
    queryFn: () =>
      fetchLeaderboard({
        day_filter: dayFilter,
        day_from: effectiveDayFrom,
        day_to: effectiveDayTo,
      }),
    enabled: mode === 'stored',
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: uploadChat,
    onSuccess: (result) => {
      alert(`Added ${result.added} game entries! Total: ${result.total}`)
      queryClient.invalidateQueries({ queryKey: ['leaderboard'] })
      queryClient.invalidateQueries({ queryKey: ['dates'] })
      setMode('stored')
    },
  })

  const handleFileUpload = () => {
    const file = fileInputRef.current?.files?.[0]
    if (file) {
      uploadMutation.mutate(file)
    }
  }

  const rankingTypes = dayFilter === 'All' ? RANKING_TYPES_ALL : RANKING_TYPES_DAY

  // Dates available after dayFrom for end filter
  const daysAfterFrom = dates.filter((d) => d >= (effectiveDayFrom ?? ''))

  return (
    <div>
      {/* Champion image */}
      <div className="flex justify-center mb-6">
        <div className="text-center">
          <img
            src="/anto.png"
            alt="Champion"
            className="w-48 h-48 object-cover rounded-lg mx-auto"
          />
          <p className="text-sm text-gray-400 mt-2">
            Antonio Roberto Ventura, 2026 Spring Champion
          </p>
        </div>
      </div>

      <h1 className="text-3xl font-bold mb-6">LinkedIn Mini Games Leaderboard</h1>

      {/* Data source toggle */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setMode('stored')}
          className={`px-4 py-2 rounded ${mode === 'stored' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
        >
          Use Stored Data
        </button>
        <button
          onClick={() => setMode('upload')}
          className={`px-4 py-2 rounded ${mode === 'upload' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
        >
          Upload New Data
        </button>
      </div>

      {/* Upload section */}
      {mode === 'upload' && (
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <label className="block mb-2 text-sm">Upload new WhatsApp chat (.txt)</label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt"
            className="block mb-3 text-sm text-gray-400"
          />
          <button
            onClick={handleFileUpload}
            disabled={uploadMutation.isPending}
            className="px-4 py-2 bg-green-600 rounded hover:bg-green-500 disabled:opacity-50"
          >
            {uploadMutation.isPending ? 'Uploading...' : 'Upload & Process'}
          </button>
        </div>
      )}

      {/* Day filter */}
      {mode === 'stored' && (
        <>
          <div className="mb-4">
            <h2 className="text-xl font-semibold mb-2">Filter by day</h2>
            <select
              value={dayFilter}
              onChange={(e) => {
                setDayFilter(e.target.value)
                setRankingType('Total Points')
              }}
              className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="All">All</option>
              {dates.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Date range when "All" */}
          {dayFilter === 'All' && (
            <div className="flex gap-4 mb-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Start date (defaults to {defaultStart})
                </label>
                <select
                  value={effectiveDayFrom ?? defaultStart}
                  onChange={(e) => setDayFrom(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                >
                  <option value={defaultStart}>{defaultStart}</option>
                  {dates.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  End date (defaults to {dates[0] ?? 'latest'})
                </label>
                <select
                  value={effectiveDayTo ?? dates[0] ?? ''}
                  onChange={(e) => setDayTo(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                >
                  {daysAfterFrom.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Ranking type toggle */}
          <div className="flex flex-wrap gap-2 mb-6">
            {rankingTypes.map((type) => (
              <button
                key={type}
                onClick={() => setRankingType(type)}
                className={`px-3 py-1.5 rounded text-sm ${
                  rankingType === type ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Loading / Error */}
          {isLoading && <p className="text-gray-400">Loading rankings...</p>}
          {error && <p className="text-red-400">Error loading data.</p>}

          {/* Rankings display */}
          {leaderboard && !leaderboard.error && (
            <div>
              {rankingType === 'Total Points' && (
                <section>
                  <h2 className="text-xl font-semibold mb-3">Total Scores</h2>
                  <DataTable data={leaderboard.total_score} />
                  <p className="text-xs text-gray-500 mt-2 italic">
                    Note: Total scores are computed by awarding 5 points for the best player,
                    3 points for the second-best player, and 1 point for the third-best player, per game per day.
                  </p>
                </section>
              )}

              {rankingType === 'Total Time' && (
                <section>
                  <h2 className="text-xl font-semibold mb-3">Total Times</h2>
                  <DataTable data={leaderboard.total_times} />
                  <p className="text-xs text-gray-500 mt-2 italic">
                    Note: For players who did not play all games, their total time has been adjusted
                    as if they had played all games at their average time.
                  </p>
                </section>
              )}

              {rankingType === 'Average Time' && (
                <section>
                  <h2 className="text-xl font-semibold mb-3">Average Times per Game</h2>
                  <DataTable data={leaderboard.average_times} />
                </section>
              )}

              {rankingType === 'Times N°1' && (
                <section>
                  <h2 className="text-xl font-semibold mb-3">Overall Times N°1</h2>
                  <DataTable data={leaderboard.overall_best} />
                </section>
              )}

              {rankingType === 'Weekday Scores' && (
                <section>
                  <h2 className="text-xl font-semibold mb-3">Overall Weekday Scores</h2>
                  <DataTable data={leaderboard.weekday_scores} />
                </section>
              )}

              {rankingType === 'Times N°1 per Weekday' && (
                <section>
                  <h2 className="text-xl font-semibold mb-3">Times N°1 per Weekday</h2>
                  <DataTable data={leaderboard.weekday_best} />
                </section>
              )}

              {/* Per-game rankings */}
              <section className="mt-8">
                <h2 className="text-xl font-semibold mb-4">Per-Game Rankings</h2>
                {Object.entries(leaderboard.per_game_rankings).map(([game, rows]) => (
                  <div key={game} className="mb-6">
                    <h3 className="text-lg font-medium mb-2">{game} Rankings</h3>
                    <DataTable data={rows as Record<string, unknown>[]} />
                  </div>
                ))}
              </section>
            </div>
          )}

          {leaderboard?.error && (
            <p className="text-yellow-400">{leaderboard.error}</p>
          )}
        </>
      )}
    </div>
  )
}
