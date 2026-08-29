const SUPER_LABELS = {
  mercadona:     'Mercadona',
  carrefour:     'Carrefour',
  bonpreu:       'Bonpreu / Esclat',
  elcorteingles: 'El Corte Inglés',
  alcampo:       'Alcampo',
}

export default function PriceSummary({ summary, supermarket, date }) {
  if (!summary) return null

  const { totals_by_super, cheapest_supermarket, cheapest_total, potential_savings, total_paid } = summary
  const fmt = (n) => `${Number(n).toFixed(2)} €`

  return (
    <div className="space-y-4">
      {/* Receipt info bar */}
      <div className="bg-white rounded-xl border border-gray-200 px-6 py-4 flex items-center justify-between flex-wrap gap-3">
        <div>
          <span className="text-sm text-gray-500">Detected supermarket: </span>
          <span className="font-medium text-gray-900 capitalize">
            {SUPER_LABELS[supermarket] || supermarket || 'Unknown'}
          </span>
        </div>
        {date && (
          <div className="text-sm text-gray-500">
            {new Date(date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
          </div>
        )}
        <div>
          <span className="text-sm text-gray-500">Total paid: </span>
          <span className="font-bold text-gray-900">{fmt(total_paid)}</span>
        </div>
      </div>

      {/* Totals grid — 5 columns */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {Object.entries(totals_by_super).map(([super_name, total]) => {
          const isCheapest = super_name === cheapest_supermarket
          return (
            <div
              key={super_name}
              className={`rounded-xl border p-4 ${
                isCheapest
                  ? 'bg-green-50 border-green-300'
                  : 'bg-white border-gray-200'
              }`}
            >
              <div className={`text-xs font-medium mb-1 leading-tight ${
                isCheapest ? 'text-green-700' : 'text-gray-500'
              }`}>
                {SUPER_LABELS[super_name]}
                {isCheapest && <span className="ml-1">🏆</span>}
              </div>
              <div className={`text-xl font-bold ${
                isCheapest ? 'text-green-800' : 'text-gray-800'
              }`}>
                {total > 0 ? fmt(total) : '—'}
              </div>
              {isCheapest && potential_savings > 0 && (
                <div className="text-xs text-green-600 mt-1">
                  Save {fmt(potential_savings)}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
