import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import History from './pages/History'
import Analytics from './pages/Analytics'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <a href="/" className="text-xl font-bold text-gray-900">
            Stalv<span className="text-green-600">IA</span>
          </a>
          <div className="flex gap-6 text-sm text-gray-600">
            <a href="/" className="hover:text-gray-900">Analitza</a>
            <a href="/historial" className="hover:text-gray-900">Historial</a>
            <a href="/analytics" className="hover:text-gray-900">Analítica</a>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/historial" element={<History />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
      </main>
    </div>
  )
}
