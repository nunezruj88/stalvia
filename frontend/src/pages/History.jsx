import { useState, useEffect } from 'react'
import { getPurchases, getPurchase } from '../services/api'

const SUPER_LABELS = {
  mercadona: 'Mercadona', carrefour: 'Carrefour', bonpreu: 'Bonpreu',
  elcorteingles: 'El Corte Inglés', alcampo: 'Alcampo',
}

const fmt = (n) => n != null ? `${Number(n).toFixed(2)} €` : '—'

function PurchaseCard({ purchase, onClick }) {
  return (
    <button
      onClick={() => onClick(purchase.id)}
      className="w-full bg-white rounded-xl border border-slate-200 px-5 py-4 text-left hover:border-green-300 hover:shadow-sm transition-all group"
    >
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold text-slate-800 capitalize">
            {SUPER_LABELS[purchase.supermarket] || purchase.supermarket || 'Unknown'}
          </div>
          <div className="text-sm text-slate-400 mt-0.5">
            {new Date(purchase.purchase_date).toLocaleDateString('en-GB', {
              day: 'numeric', month: 'short', year: 'numeric'
            })}
            {' · '}
            {purchase.item_count} items
          </div>
        </div>
        <div className="text-right">
          <div className="font-bold text-slate-900 mono">{fmt(purchase.total_amount)}</div>
          <div className="text-xs text-slate-300 mt-1 group-hover:text-green-500 transition-colors">
            View details →
          </div>
        </div>
      </div>
    </button>
  )
}

function PurchaseDetail({ purchase, onClose }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <div className="font-semibold text-slate-900">
            {SUPER_LABELS[purchase.supermarket] || purchase.supermarket || 'Unknown'}
          </div>
          <div className="text-sm text-slate-400">
            {new Date(purchase.purchase_date).toLocaleDateString('en-GB', {
              weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
            })}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs text-slate-400">Total</div>
            <div className="font-bold text-slate-900 mono">{fmt(purchase.total_amount)}</div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-300 hover:text-slate-600 text-xl transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-50 text-slate-400 text-xs uppercase">
            <th className="text-left px-5 py-3 font-medium">Product</th>
            <th className="text-right px-4 py-3 font-medium">Qty</th>
            <th className="text-right px-4 py-3 font-medium">Unit price</th>
            <th className="text-right px-5 py-3 font-medium">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {purchase.items?.map(item => (
            <tr key={item.id} className="hover:bg-slate-50">
              <td className="px-5 py-3">
                <div className="font-medium text-slate-800">{item.canonical_name || item.raw_name}</div>
                {item.canonical_name && item.raw_name !== item.canonical_name && (
                  <div className="text-xs text-slate-400">{item.raw_name}</div>
                )}
              </td>
              <td className="px-4 py-3 text-right text-slate-500 mono">{item.quantity}</td>
              <td className="px-4 py-3 text-right text-slate-600 mono">{fmt(item.unit_price)}</td>
              <td className="px-5 py-3 text-right font-semibold text-slate-800 mono">{fmt(item.total_price)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function History() {
  const [purchases, setPurchases] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    getPurchases()
      .then(data => setPurchases(data.purchases || data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleSelect = async (id) => {
    setSelected(id)
    try {
      const data = await getPurchase(id)
      setDetail(data)
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) return (
    <div className="flex justify-center py-16">
      <svg className="animate-spin h-6 w-6 text-green-500" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
    </div>
  )

  if (!purchases.length) return (
    <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
      <div className="text-4xl mb-3">🧾</div>
      <h2 className="font-semibold text-slate-700 mb-1">No receipts yet</h2>
      <p className="text-slate-400 text-sm">Scan your first receipt to start tracking prices.</p>
    </div>
  )

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-slate-900">Purchase history</h1>

      {detail && (
        <PurchaseDetail purchase={detail} onClose={() => { setDetail(null); setSelected(null) }} />
      )}

      <div className="space-y-2">
        {purchases.map(p => (
          <PurchaseCard
            key={p.id}
            purchase={p}
            onClick={handleSelect}
          />
        ))}
      </div>
    </div>
  )
}
