import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import History from './pages/History'
import Analytics from './pages/Analytics'

const NAV = [
  { to: '/',          label: 'Scan',      icon: '📷' },
  { to: '/history',   label: 'History',   icon: '🧾' },
  { to: '/analytics', label: 'Analytics', icon: '📈' },
]

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">

      {/* Top bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight text-slate-900">
              Stalv<span className="text-green-600">IA</span>
            </span>
            <span className="hidden sm:inline text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
              Catalunya
            </span>
          </a>

          <nav className="flex items-center gap-1">
            {NAV.map(({ to, label, icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-green-50 text-green-700'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
                  }`
                }
              >
                <span>{icon}</span>
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      {/* Page content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <Routes>
          <Route path="/"          element={<Home />} />
          <Route path="/history"   element={<History />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
      </main>
    </div>
  )
}
