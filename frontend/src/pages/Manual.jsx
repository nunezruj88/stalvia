import { useState, useRef, useEffect } from 'react'
import { addManualProduct } from '../services/api'

const SUPERMARKETS = [
  { value: 'mercadona',     label: 'Mercadona' },
  { value: 'carrefour',     label: 'Carrefour' },
  { value: 'bonpreu',       label: 'Bonpreu / Esclat' },
  { value: 'elcorteingles', label: 'El Corte Inglés' },
  { value: 'alcampo',       label: 'Alcampo' },
]

const CATEGORIES = [
  { value: 'beverages',       label: '🥤 Beverages' },
  { value: 'dairy',           label: '🥛 Dairy' },
  { value: 'bakery',          label: '🍞 Bakery' },
  { value: 'meat_fish',       label: '🥩 Meat & Fish' },
  { value: 'fruits_veg',      label: '🥦 Fruits & Vegetables' },
  { value: 'frozen',          label: '🧊 Frozen' },
  { value: 'pantry',          label: '🥫 Pantry' },
  { value: 'snacks',          label: '🍿 Snacks' },
  { value: 'cleaning',        label: '🧹 Cleaning' },
  { value: 'personal_care',   label: '🧴 Personal Care' },
  { value: 'other',           label: '📦 Other' },
]

export default function Manual() {
  const [form, setForm] = useState({
    barcode: '',
    name: '',
    supermarket: '',
    category: '',
    price: '',
  })
  const [scanning, setScanning] = useState(false)
  const [status, setStatus] = useState(null) // { type: 'success'|'error', message }
  const [loading, setLoading] = useState(false)
  const videoRef = useRef(null)
  const streamRef = useRef(null)

  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }))

  // ── Barcode scanner via camera ──────────────────────────────────────────────
  const startScanner = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      })
      streamRef.current = stream
      if (videoRef.current) videoRef.current.srcObject = stream
      setScanning(true)
    } catch (e) {
      setStatus({ type: 'error', message: 'Camera not available. Enter barcode manually.' })
    }
  }

  const stopScanner = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    setScanning(false)
  }

  // Use BarcodeDetector API if available (Chrome/Android)
  useEffect(() => {
    if (!scanning || !videoRef.current) return
    if (!('BarcodeDetector' in window)) {
      setStatus({ type: 'error', message: 'Barcode detection not supported in this browser. Enter manually.' })
      stopScanner()
      return
    }

    const detector = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] })
    let active = true

    const detect = async () => {
      if (!active || !videoRef.current) return
      try {
        const barcodes = await detector.detect(videoRef.current)
        if (barcodes.length > 0) {
          setForm(f => ({ ...f, barcode: barcodes[0].rawValue }))
          stopScanner()
          setStatus({ type: 'success', message: `Barcode detected: ${barcodes[0].rawValue}` })
          return
        }
      } catch (_) {}
      if (active) setTimeout(detect, 300)
    }

    videoRef.current.onloadedmetadata = () => detect()
    return () => { active = false }
  }, [scanning])

  useEffect(() => () => stopScanner(), [])

  // ── Submit ──────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!form.name.trim()) {
      setStatus({ type: 'error', message: 'Product name is required.' })
      return
    }
    if (!form.supermarket) {
      setStatus({ type: 'error', message: 'Please select a supermarket.' })
      return
    }
    if (!form.price || isNaN(parseFloat(form.price))) {
      setStatus({ type: 'error', message: 'Please enter a valid price.' })
      return
    }

    setLoading(true)
    setStatus(null)
    try {
      await addManualProduct(form)
      setStatus({ type: 'success', message: `"${form.name}" saved successfully.` })
      setForm({ barcode: '', name: '', supermarket: '', category: '', price: '' })
    } catch (e) {
      setStatus({ type: 'error', message: e.message || 'Something went wrong.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5 max-w-lg">
      <h1 className="text-xl font-bold text-slate-900">Add product manually</h1>
      <p className="text-slate-400 text-sm -mt-3">
        Manually register a product price to build the local database.
      </p>

      {/* Status */}
      {status && (
        <div className={`rounded-xl px-4 py-3 text-sm flex items-center gap-2 ${
          status.type === 'success'
            ? 'bg-green-50 border border-green-200 text-green-800'
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          <span>{status.type === 'success' ? '✓' : '⚠️'}</span>
          {status.message}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-5">

        {/* Barcode */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Barcode <span className="text-slate-400 font-normal">(optional)</span>
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={form.barcode}
              onChange={set('barcode')}
              placeholder="e.g. 8410175222040"
              className="flex-1 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent mono"
            />
            <button
              onClick={scanning ? stopScanner : startScanner}
              className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                scanning
                  ? 'bg-red-50 border border-red-200 text-red-600 hover:bg-red-100'
                  : 'bg-slate-100 border border-slate-200 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {scanning ? '✕ Stop' : '📷 Scan'}
            </button>
          </div>

          {/* Camera preview */}
          {scanning && (
            <div className="mt-3 rounded-xl overflow-hidden border border-slate-200 bg-black relative">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full max-h-48 object-cover"
              />
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="border-2 border-green-400 rounded-lg w-48 h-20 opacity-70" />
              </div>
              <p className="text-center text-white text-xs py-2 bg-black/50">
                Point camera at barcode
              </p>
            </div>
          )}
        </div>

        {/* Product name */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Product name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={form.name}
            onChange={set('name')}
            placeholder="e.g. Leche entera Hacendado 1L"
            className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
          />
          <p className="text-xs text-slate-400 mt-1">Use the name as it appears on the receipt</p>
        </div>

        {/* Supermarket */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Supermarket <span className="text-red-400">*</span>
          </label>
          <select
            value={form.supermarket}
            onChange={set('supermarket')}
            className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white"
          >
            <option value="">Select supermarket…</option>
            {SUPERMARKETS.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Category <span className="text-slate-400 font-normal">(optional)</span>
          </label>
          <select
            value={form.category}
            onChange={set('category')}
            className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent bg-white"
          >
            <option value="">Select category…</option>
            {CATEGORIES.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        {/* Price */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Price (€) <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.price}
              onChange={set('price')}
              placeholder="0.00"
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent mono pr-10"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">€</span>
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full bg-green-600 hover:bg-green-700 active:bg-green-800 disabled:bg-green-300 text-white font-medium py-3 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              Saving…
            </>
          ) : (
            '+ Save product'
          )}
        </button>
      </div>
    </div>
  )
}
