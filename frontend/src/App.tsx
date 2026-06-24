import { useState } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import LeaderboardPage from './pages/LeaderboardPage'
import HeadToHeadPage from './pages/HeadToHeadPage'

export default function App() {
  const [navOpen, setNavOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Mobile hamburger button */}
      <button
        onClick={() => setNavOpen(true)}
        className="fixed top-4 left-4 z-50 md:hidden bg-gray-800 p-2 rounded text-gray-300 hover:text-white"
        aria-label="Open navigation"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Overlay (mobile only) */}
      {navOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setNavOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <nav
        className={`fixed left-0 top-0 h-full w-56 bg-gray-800 border-r border-gray-700 p-6 flex flex-col gap-4 z-50 transition-transform duration-200 ${
          navOpen ? 'translate-x-0' : '-translate-x-full'
        } md:translate-x-0`}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Navigation</h2>
          <button
            onClick={() => setNavOpen(false)}
            className="md:hidden text-gray-400 hover:text-white"
            aria-label="Close navigation"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <NavLink
          to="/"
          onClick={() => setNavOpen(false)}
          className={({ isActive }) =>
            `block px-4 py-2 rounded ${isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`
          }
        >
          Leaderboard
        </NavLink>
        <NavLink
          to="/head-to-head"
          onClick={() => setNavOpen(false)}
          className={({ isActive }) =>
            `block px-4 py-2 rounded ${isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`
          }
        >
          1v1 Head-to-Head
        </NavLink>
      </nav>

      {/* Main content */}
      <main className="md:ml-56 p-8 pt-16 md:pt-8">
        <Routes>
          <Route path="/" element={<LeaderboardPage />} />
          <Route path="/head-to-head" element={<HeadToHeadPage />} />
        </Routes>
      </main>
    </div>
  )
}
