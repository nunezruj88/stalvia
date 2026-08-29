const BASE_URL = '/api'

export async function analyzeTicket(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${BASE_URL}/analyze-ticket`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) throw new Error(`Error ${res.status}: ${res.statusText}`)
  return res.json()
}

export async function getPurchases() {
  const res = await fetch(`${BASE_URL}/purchases`)
  if (!res.ok) throw new Error(`Error ${res.status}`)
  return res.json()
}

export async function getPriceHistory(productId) {
  const res = await fetch(`${BASE_URL}/price-history/${productId}`)
  if (!res.ok) throw new Error(`Error ${res.status}`)
  return res.json()
}
