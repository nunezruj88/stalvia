const BASE = '/api'
const handle = async res => {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = Array.isArray(err.detail) ? err.detail.map(e => e.msg).join('; ') : err.detail
    throw new Error(detail || `Error ${res.status}`)
  }
  return res.json()
}
export const analyzeTicket = async file => {
  const body = new FormData(); body.append('file', file)
  return handle(await fetch(`${BASE}/analyze-ticket`, { method: 'POST', body }))
}
const post = async (path, data) => handle(await fetch(`${BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }))
export const saveReceipt = data => post('/purchases', data)
export const compareProduct = data => post('/compare-product', data)
export const addManualProduct = data => post('/products/manual', data)
export const getPurchases = async (skip = 0, limit = 50) => handle(await fetch(`${BASE}/purchases?skip=${skip}&limit=${limit}`))
export const getPurchase = async id => handle(await fetch(`${BASE}/purchases/${id}`))
export const getProducts = async (search = '') => handle(await fetch(`${BASE}/products?search=${encodeURIComponent(search)}`))
export const getPriceHistory = async (id, store = '', days = 180) => handle(await fetch(`${BASE}/price-history/${id}?supermarket=${encodeURIComponent(store)}&days=${days}`))
export const getCheapestSuper = async (days = 30) => handle(await fetch(`${BASE}/analytics/cheapest-super?days=${days}`))
export const getSpending = async () => handle(await fetch(`${BASE}/analytics/spending`))
