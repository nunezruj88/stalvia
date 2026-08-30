import { useState, useRef } from 'react'
import { analyzeTicket } from '../services/api'
import ComparisonTable from '../components/ComparisonTable'
import PriceSummary from '../components/PriceSummary'

export default function Home() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef()

  const processFile = async (file) => {
    if (!file || !file.type.startsWith('image/')) {
      setError('Please upload an image file.')
      return
    }
    setPreview(URL.createObjectURL(file))
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await analyzeTicket(file)
      setResult(data)
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleFile = (e) => processFile(e.target.files[0])
  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    processFile(e.dataTransfer.files[0])
  }
  const handleReset = () => {
    setResult(null)
    setPreview(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="space-y-6">

      {/* Upload zone */}
      {!result && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`relative bg-white rounded-2xl border-2 border-dashed transition-colors p-10 text-center ${
            dragOver
              ? 'border-green-400 bg-green-50'
              : 'border-slate-200 hover:border-slate-300'
          }`}
        >
          {!preview ? (
            <>
              <div className="text-5xl mb-4">🧾</div>
              <h1 className="text-2xl font-bold text-slate-900 mb-1">
                Scan your receipt
              </h1>
              <p className="text-slate-400 text-sm mb-6">
                Upload a photo and StalvIA will compare prices across 5 supermarkets
              </p>
              <label className="cursor-pointer inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 active:bg-green-800 text-white px-5 py-2.5 rounded-xl font-medium text-sm transition-colors">
                <span>Choose photo</span>
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  className="hidden"
                  onChange={handleFile}
                />
              </label>
              <p className="text-slate-300 text-xs mt-3">or drag & drop here</p>
            </>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <img
                src={preview}
                alt="Receipt preview"
                className="max-h-56 rounded-xl shadow-md object-contain"
              />
              {!loading && (
                <button
                  onClick={handleReset}
                  className="text-sm text-slate-400 hover:text-slate-600 underline underline-offset-2"
                >
                  Upload a different receipt
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="bg-white rounded-2xl border border-slate-200 p-10 text-center">
          <div className="flex justify-center mb-4">
            <svg className="animate-spin h-8 w-8 text-green-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
          </div>
          <p className="text-slate-600 font-medium">Analysing receipt with AI…</p>
          <p className="text-slate-400 text-sm mt-1">Fetching prices from 5 supermarkets</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-5 flex items-start gap-3">
          <span className="text-red-400 text-lg mt-0.5">⚠️</span>
          <div>
            <p className="text-red-800 font-medium text-sm">Error</p>
            <p className="text-red-600 text-sm mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">Results</h2>
            <button
              onClick={handleReset}
              className="text-sm text-slate-400 hover:text-slate-600 flex items-center gap-1"
            >
              ← Scan another
            </button>
          </div>
          <PriceSummary summary={result.summary} supermarket={result.supermarket} date={result.date} />
          <ComparisonTable products={result.products} />
        </div>
      )}
    </div>
  )
}
