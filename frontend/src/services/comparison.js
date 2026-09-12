export const STORES = ['mercadona', 'carrefour', 'bonpreu', 'elcorteingles', 'alcampo']
export function summarize(products, count = products.length) {
  const totals_by_super = {}, coverage = {}
  for (const store of STORES) {
    const matched = products.filter(p => p.prices?.[store]?.comparable && Number(p.prices[store].price) > 0)
    coverage[store] = matched.length
    totals_by_super[store] = count > 0 && matched.length === count ? Math.round(matched.reduce((n, p) => n + Number(p.prices[store].price) * Number(p.quantity) * 100, 0)) / 100 : null
  }
  const total_paid = Math.round(products.reduce((n, p) => n + Number(p.total_price) * 100, 0)) / 100
  const complete = Object.entries(totals_by_super).filter(([, n]) => n != null).sort((a, b) => a[1] - b[1])
  const cheapest = complete[0]
  return { totals_by_super, coverage, product_count: count, total_paid, cheapest_supermarket: cheapest?.[0], cheapest_total: cheapest?.[1], potential_savings: cheapest ? Math.max(0, Math.round((total_paid - cheapest[1]) * 100) / 100) : 0 }
}
