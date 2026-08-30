const fmt = (n) => n != null ? `${Number(n).toFixed(2)} €` : '—'

export default function ProductRow({ product, supers }) {
  const prices = supers.map(s => product.prices?.[s]?.price).filter(v => v != null)
  const minPrice = prices.length > 0 ? Math.min(...prices) : null
  const maxPrice = prices.length > 0 ? Math.max(...prices) : null

  return (
    <tr className="hover:bg-slate-50 transition-colors group">
      {/* Product name */}
      <td className="px-5 py-3 max-w-xs">
        <div className="font-medium text-slate-800 leading-snug">
          {product.canonical_name || product.raw_name}
        </div>
        {product.canonical_name && product.raw_name !== product.canonical_name && (
          <div className="text-xs text-slate-400 mt-0.5 truncate">{product.raw_name}</div>
        )}
        {product.quantity > 1 && (
          <div className="text-xs text-slate-400">× {product.quantity}</div>
        )}
      </td>

      {/* Price paid */}
      <td className="px-4 py-3 text-right">
        <span className="text-slate-400 mono text-sm">
          {fmt(product.price_paid)}
        </span>
      </td>

      {/* Price per supermarket */}
      {supers.map(s => {
        const item = product.prices?.[s]
        const price = item?.price
        const isBest = price != null && price === minPrice
        const isWorst = price != null && price === maxPrice && minPrice !== maxPrice
        const diff = price != null && minPrice != null && price !== minPrice
          ? `+${(price - minPrice).toFixed(2)}`
          : null

        return (
          <td key={s} className="px-4 py-3 text-right">
            {price != null ? (
              <div className="flex flex-col items-end">
                <span className={`mono font-semibold text-sm ${
                  isBest ? 'text-green-600' : isWorst ? 'text-red-400' : 'text-slate-700'
                }`}>
                  {fmt(price)}
                  {isBest && <span className="ml-1 text-green-500 text-xs">✓</span>}
                </span>
                {diff && (
                  <span className="text-xs text-slate-300 mono">{diff}</span>
                )}
              </div>
            ) : (
              <span className="text-slate-200">—</span>
            )}
          </td>
        )
      })}
    </tr>
  )
}
