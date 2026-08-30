import { useState, useEffect } from 'react'
import { getCheapestSuper, getSpending } from '../services/api'

const SUPER_LABELS = {
  mercadona: 'Mercadona', carrefour: 'Carrefour', bonpreu: 'Bonpreu',
  elcorteingles: 'El Corte Inglés', alcampo: 'Alcampo',
}

const SUPER_COLORS = {
  mercadona: 'bg-red-400', carrefour: 'bg-blue-400',
  bonpreu: 'bg-orange-400', elcorteingles: 'bg-sky-400', alcampo: 'bg-purple-400',
}

const fmt = (n) => n != null ? `${Number(n).toFixed(2)} €` : '—'

function BarChart({ data, maxVal, color }) {
  return (
    <div className="space-y-2">
      {data.map(({ label, value, sublabel }) => (
        <div key={label} className="flex items-center gap-3">
          <div className="w-28 text-xs text-slate-500 text-right truncate shrink-0">{label}</div>
          <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${color}`}
              style={{ width: `${Math.min(100, (value / maxVal) * 100)}%` }}
            />
          </div>
          <div className="w-20 text-xs font-semibold text-slate-700 mono shrink-0">{sublabel}</div>
        </div>
      ))}
    </div>
  )
}

export default function Analytics() {
  const [cheapest, setCheapest] = useState([])
  const [spending, setSpending] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getCheapestSuper(), getSpending()])
      .then(([c, s]) => { setCheapest(c); setSpending(s) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const isEmpty = !cheapest.length && !spending.length

  if (loading) return (
    <div className="flex justify-center py-16">
      <svg className="animate-spin h-6 w-6 text-green-500" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
    </div>
  )

  if (isEmpty) return (
    <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
      <div className="text-4xl mb-3">📈</div>
      <h2 className="font-semibold text-slate-700 mb-1">No data yet</h2>
      <p className="text-slate-400 text-sm">Scan a few receipts to start seeing price trends.</p>
    </div>
  )

  const maxAvg = Math.max(...cheapest.map(c => c.avg_price), 0)
  const maxSpend = Math.max(...spending.map(s => s.total), 0)

  const totalSpend = spending.reduce((acc, s) => acc + s.total, 0)
  const totalPurchases = spending.reduce((acc, s) => acc + s.purchase_count, 0)

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-slate-900">Analytics</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="text-xs text-slate-400 mb-1">Total spent</div>
          <div className="text-2xl font-bold text-slate-900 mono">{fmt(totalSpend)}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="text-xs text-slate-400 mb-1">Purchases</div>
          <div className="text-2xl font-bold text-slate-900 mono">{totalPurchases}</div>
        </div>
        {cheapest[0] && (
          <div className="bg-green-50 rounded-xl border border-green-200 p-4">
            <div className="text-xs text-green-600 mb-1">Cheapest on average</div>
            <div className="text-lg font-bold text-green-800">
              {SUPER_LABELS[cheapest[0].supermarket] || cheapest[0].supermarket}
            </div>
            <div className="text-xs text-green-600 mono mt-0.5">{fmt(cheapest[0].avg_price)} avg</div>
          </div>
        )}
      </div>

      {/* Cheapest supermarket */}
      {cheapest.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Average price by supermarket <span className="text-slate-400 font-normal text-sm">(last 30 days)</span></h3>
          <BarChart
            data={cheapest.map(c => ({
              label: SUPER_LABELS[c.supermarket] || c.supermarket,
              value: c.avg_price,
              sublabel: `${fmt(c.avg_price)}`,
            }))}
            maxVal={maxAvg}
            color="bg-green-400"
          />
        </div>
      )}

      {/* Monthly spending */}
      {spending.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Monthly spending</h3>
          <BarChart
            data={spending.map(s => ({
              label: s.month,
              value: s.total,
              sublabel: fmt(s.total),
            }))}
            maxVal={maxSpend}
            color="bg-blue-400"
          />
        </div>
      )}
    </div>
  )
}
