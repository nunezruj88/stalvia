import { useState } from 'react'
import { analyzeTicket } from '../services/api'
import ComparisonTable from '../components/ComparisonTable'
import PriceSummary from '../components/PriceSummary'

export default function Home() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)

  const handleFile = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    setPreview(URL.createObjectURL(file))
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await analyzeTicket(file)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Upload */}
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Analitza el teu tiquet
        </h1>
        <p className="text-gray-500 mb-6">
          Fes una foto del tiquet i StalvIA compararà els preus als 3 supers
        </p>

        <label className="cursor-pointer inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium transition-colors">
          <span>📷 Puja el tiquet</span>
          <input type="file" accept="image/*" className="hidden" onChange={handleFile} />
        </label>

        {preview && (
          <div className="mt-6">
            <img src={preview} alt="Tiquet" className="max-h-48 mx-auto rounded-lg shadow" />
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="animate-spin text-4xl mb-4">⚙️</div>
          <p className="text-gray-600">Analitzant tiquet amb IA i cercant preus...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
          ⚠️ {error}
        </div>
      )}

      {/* Resultats */}
      {result && (
        <div className="space-y-6">
          <PriceSummary summary={result.summary} supermarket={result.supermarket} date={result.date} />
          <ComparisonTable products={result.products} />
        </div>
      )}
    </div>
  )
}
