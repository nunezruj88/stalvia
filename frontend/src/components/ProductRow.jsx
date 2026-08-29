const SUPERS = ['mercadona', 'carrefour', 'bonpreu']

export default function ProductRow({ product }) {
  const prices = SUPERS.map(s => product.prices?.[s]?.price).filter(Boolean)
  const minPrice = prices.length > 0 ? Math.min(...prices) : null

  const fmt = (n) => n != null ? `${Number(n).toFixed(2)} €` : '—'

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-6 py-3">
        <div className="font-medium text-gray-900">{product.canonical_name}</div>
        {product.raw_name !== product.canonical_name && (
          <div className="text-xs text-gray-400">{product.raw_name}</div>
        )}
        {product.quantity > 1 && (
          <div className="text-xs text-gray-400">× {product.quantity}</div>
        )}
      </td>

      <td className="px-4 py-3 text-right text-gray-500">
        {fmt(product.price_paid)}
      </td>

      {SUPERS.map(s => {
        const item = product.prices?.[s]
        const price = item?.price
        const isBest = price != null && price === minPrice

        return (
          <td key={s} className="px-4 py-3 text-right">
            {price != null ? (
              <span className={`font-medium ${isBest ? 'text-green-600' : 'text-gray-700'}`}>
                {fmt(price)}
                {isBest && <span className="ml-1 text-green-500">✓</span>}
              </span>
            ) : (
              <span className="text-gray-300">—</span>
            )}
          </td>
        )
      })}
    </tr>
  )
}
