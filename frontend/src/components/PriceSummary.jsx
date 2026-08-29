const SUPER_LABELS = {
  mercadona: 'Mercadona',
  carrefour: 'Carrefour',
  bonpreu: 'Bonpreu / Esclat',
}

const SUPER_COLORS = {
  mercadona: 'bg-red-50 border-red-200 text-red-800',
  carrefour: 'bg-blue-50 border-blue-200 text-blue-800',
  bonpreu: 'bg-orange-50 border-orange-200 text-orange-800',
}

export default function PriceSummary({ summary, supermarket, date }) {
  if (!summary) return null

  const { totals_by_super, cheapest_supermarket, cheapest_total, potential_savings, total_paid } = summary
  const fmt = (n) => `${Number(n).toFixed(2)} €`

  return (
    <div className="space-y-4">
      {/* Info tiquet */}
      <div className="bg-white rounded-xl border border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <span className="text-sm text-gray-500">Supermercat detectat: </span>
          <span className="font-medium text-gray-900 capitalize">{supermarket || 'Desconegut'}</span>
        </div>
        {date && (
          <div className="text-sm text-gray-500">
            {new Date(date).toLocaleDateString('ca-ES', { day: 'numeric', month: 'long', year: 'numeric' })}
          </div>
        )}
        <div>
          <span className="text-sm text-gray-500">Total pagat: </span>
          <span className="font-bold text-gray-900">{fmt(total_paid)}</span>
        </div>
      </div>

      {/* Totals per super */}
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(totals_by_super).map(([super_name, total]) => {
          const isCheapest = super_name === cheapest_supermarket
          return (
            <div
              key={super_name}
              className={`rounded-xl border p-5 ${isCheapest
                ? 'bg-green-50 border-green-300'
                : 'bg-white border-gray-200'
              }`}
            >
              <div className={`text-sm font-medium mb-1 ${isCheapest ? 'text-green-700' : 'text-gray-500'}`}>
                {SUPER_LABELS[super_name]}
                {isCheapest && <span className="ml-2">🏆</span>}
              </div>
              <div className={`text-2xl font-bold ${isCheapest ? 'text-green-800' : 'text-gray-800'}`}>
                {total > 0 ? fmt(total) : '—'}
              </div>
              {isCheapest && potential_savings > 0 && (
                <div className="text-xs text-green-600 mt-1">
                  Estalvi: {fmt(potential_savings)}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
