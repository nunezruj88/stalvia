const SUPER_LABELS = {
  mercadona:     'Mercadona',
  carrefour:     'Carrefour',
  bonpreu:       'Bonpreu',
  elcorteingles: 'El Corte Inglés',
  alcampo:       'Alcampo',
}

const SUPER_COLORS = {
  mercadona:     'bg-red-50    border-red-200    text-red-800',
  carrefour:     'bg-blue-50   border-blue-200   text-blue-800',
  bonpreu:       'bg-orange-50 border-orange-200 text-orange-800',
  elcorteingles: 'bg-sky-50    border-sky-200    text-sky-800',
  alcampo:       'bg-purple-50 border-purple-200 text-purple-800',
}

const fmt = (n) => n != null ? `${Number(n).toFixed(2)} €` : '—'

export default function PriceSummary({ summary, supermarket, date }) {
  if (!summary) return null

  const { totals_by_super, cheapest_supermarket, potential_savings, total_paid } = summary

  const validTotals = Object.entries(totals_by_super)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => a - b)

  return (
    <div className="space-y-3">

      {/* Receipt meta */}
      <div className="bg-white rounded-2xl border border-slate-200 px-5 py-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        {supermarket && supermarket !== 'unknown' && (
          <div>
            <span className="text-slate-400">Scanned at </span>
            <span className="font-semibold text-slate-800 capitalize">
              {SUPER_LABELS[supermarket] || supermarket}
            </span>
          </div>
        )}
        {date && (
          <div>
            <span className="text-slate-400">Date </span>
            <span className="font-semibold text-slate-800">
              {new Date(date).toLocaleDateString('en-GB', {
                day: 'numeric', month: 'short', year: 'numeric'
              })}
            </span>
          </div>
        )}
        <div className="ml-auto">
          <span className="text-slate-400">Paid </span>
          <span className="font-bold text-slate-900 mono">{fmt(total_paid)}</span>
        </div>
        {potential_savings > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg px-3 py-1">
            <span className="text-green-700 font-semibold text-sm">
              Save up to {fmt(potential_savings)} at {SUPER_LABELS[cheapest_supermarket] || cheapest_supermarket}
            </span>
          </div>
        )}
      </div>

      {/* Super totals grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {validTotals.map(([name, total], i) => {
          const isCheapest = i === 0
          return (
            <div
              key={name}
              className={`rounded-xl border p-4 transition-all ${
                isCheapest
                  ? 'bg-green-50 border-green-300 ring-1 ring-green-300'
                  : 'bg-white border-slate-200'
              }`}
            >
              <div className={`text-xs font-semibold mb-2 flex items-center justify-between ${
                isCheapest ? 'text-green-700' : 'text-slate-400'
              }`}>
                <span className="truncate">{SUPER_LABELS[name]}</span>
                {isCheapest && <span className="ml-1 shrink-0">🏆</span>}
              </div>
              <div className={`text-lg font-bold mono ${
                isCheapest ? 'text-green-800' : 'text-slate-700'
              }`}>
                {fmt(total)}
              </div>
              {isCheapest && potential_savings > 0 && (
                <div className="text-xs text-green-600 mt-1 font-medium">
                  cheapest
                </div>
              )}
              {!isCheapest && validTotals[0] && (
                <div className="text-xs text-slate-400 mt-1">
                  +{fmt(total - validTotals[0][1])}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
