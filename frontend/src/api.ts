import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

export interface LeaderboardParams {
  day_filter?: string
  day_from?: string | null
  day_to?: string | null
}

export interface HeadToHeadParams {
  player1: string
  player2: string
  date_from?: string | null
  date_to?: string | null
  count_missing?: boolean
}

export async function fetchDates(): Promise<{ dates: string[] }> {
  const { data } = await api.get('/dates')
  return data
}

export async function fetchPlayers(): Promise<{ players: string[] }> {
  const { data } = await api.get('/players')
  return data
}

export async function fetchLeaderboard(params: LeaderboardParams) {
  const { data } = await api.get('/leaderboard', { params })
  return data
}

export async function fetchHeadToHead(params: HeadToHeadParams) {
  const { data } = await api.get('/head-to-head', { params })
  return data
}

export async function uploadChat(file: File): Promise<{ added: number; total: number }> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/upload', formData)
  return data
}
