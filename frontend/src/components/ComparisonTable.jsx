import ProductRow from './ProductRow'

const SUPERS = ['mercadona', 'carrefour', 'bonpreu', 'elcorteingles', 'alcampo']

const SUPER_LABELS = {
  mercadona:     'Mercadona',
  carrefour:     'Carrefour',
  bonpreu:       'Bonpreu / Esclat',
  elcorteingles: 'El Corte Inglés',
  alcampo:       'Alcampo',
}

export default function ComparisonTable({ products }) {
  if (!products?.length) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="font-semibold text-gray-900">Price comparison</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th className="text-left px-6 py-3 font-medium">Product</th>
              <th className="text-right px-4 py-3 font-medium">Paid</th>
              {SUPERS.map(s => (
                <th key={s} className="text-right px-4 py-3 font-medium">
                  {SUPER_LABELS[s]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {products.map((product, i) => (
              <ProductRow key={i} product={product} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
