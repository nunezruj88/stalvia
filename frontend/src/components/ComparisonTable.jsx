import ProductRow from './ProductRow'

const SUPERS = ['mercadona', 'carrefour', 'bonpreu', 'elcorteingles', 'alcampo']

const SUPER_LABELS = {
  mercadona:     'Mercadona',
  carrefour:     'Carrefour',
  bonpreu:       'Bonpreu',
  elcorteingles: 'El Corte Inglés',
  alcampo:       'Alcampo',
}

export default function ComparisonTable({ products }) {
  if (!products?.length) return null

  const found = SUPERS.filter(s =>
    products.some(p => p.prices?.[s]?.price != null)
  )

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 className="font-semibold text-slate-900">Product comparison</h3>
        <span className="text-xs text-slate-400">{products.length} items</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 text-slate-400 text-xs uppercase tracking-wide">
              <th className="text-left px-5 py-3 font-medium">Product</th>
              <th className="text-right px-4 py-3 font-medium">Paid</th>
              {found.map(s => (
                <th key={s} className="text-right px-4 py-3 font-medium whitespace-nowrap">
                  {SUPER_LABELS[s]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {products.map((product, i) => (
              <ProductRow key={i} product={product} supers={found} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
