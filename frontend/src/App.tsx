import { Routes, Route, NavLink } from 'react-router-dom'
import LeaderboardPage from './pages/LeaderboardPage'
import HeadToHeadPage from './pages/HeadToHeadPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Sidebar Navigation */}
      <nav className="fixed left-0 top-0 h-full w-56 bg-gray-800 border-r border-gray-700 p-6 flex flex-col gap-4">
        <h2 className="text-lg font-bold mb-4">Navigation</h2>
        <NavLink
          to="/"
          className={({ isActive }) =>
            `block px-4 py-2 rounded ${isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`
          }
        >
          Leaderboard
        </NavLink>
        <NavLink
          to="/head-to-head"
          className={({ isActive }) =>
            `block px-4 py-2 rounded ${isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`
          }
        >
          1v1 Head-to-Head
        </NavLink>
      </nav>

      {/* Main content */}
      <main className="ml-56 p-8">
        <Routes>
          <Route path="/" element={<LeaderboardPage />} />
          <Route path="/head-to-head" element={<HeadToHeadPage />} />
        </Routes>
      </main>
    </div>
  )
}
