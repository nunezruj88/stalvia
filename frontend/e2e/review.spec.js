import { test, expect } from '@playwright/test'

test('review, save, compare and explicitly confirm matching products', async ({ page }) => {
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const receipt = {
    supermarket: 'mercadona', date: '2026-09-01', total: '3.00', receipt_hash: 'a'.repeat(64), warnings: [],
    products: [{ raw_name: 'LECHE', canonical_name: 'Leche 1L', quantity: '2', unit_price: '2.00', total_price: '3.00', barcode: '' }],
  }
  let saved = false
  await page.route('**/api/analyze-ticket', route => route.fulfill({ json: receipt }))
  await page.route('**/api/purchases', async route => {
    expect(route.request().postDataJSON().products[0].total_price).toBe('3.00')
    saved = true
    await route.fulfill({ json: { purchase_id: 1, duplicate: false } })
  })
  await page.route('**/api/compare-product', route => route.fulfill({ json: {
    ...receipt.products[0], prices: { mercadona: { name: 'Leche 1L', price: 1.2, comparable: false, status: 'candidate', url: 'https://tienda.mercadona.es/product/1', observed_at: '2026-09-01T12:00:00Z' } },
  } }))
  await page.goto('/')
  await page.getByLabel('Foto del ticket').setInputFiles({ name: 'ticket.png', mimeType: 'image/png', buffer: Buffer.from('fixture: extraction is mocked') })
  await expect(page.getByLabel('Producto 1', { exact: true })).toHaveValue('Leche 1L')
  expect(saved).toBe(false)
  await page.getByRole('button', { name: 'Confirmar y guardar' }).click()
  await expect(page.getByText('Ticket guardado.', { exact: false })).toBeVisible()
  expect(saved).toBe(true)
  await page.getByRole('button', { name: 'Buscar precios' }).click()
  await expect(page.getByText('Búsqueda completada.', { exact: false })).toBeVisible()
  await expect(page.getByText('Menor total confirmado:', { exact: false })).toHaveCount(0)
  await page.getByRole('checkbox').check()
  await expect(page.getByText('Ahorro estimado: 0.60 €.', { exact: false })).toBeVisible()
  await page.getByRole('checkbox').uncheck()
  await expect(page.getByText('Menor total confirmado:', { exact: false })).toHaveCount(0)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: 'test-results/review-desktop.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 390)
  await page.screenshot({ path: 'test-results/review-mobile.png', fullPage: true })
  expect(errors).toEqual([])
})

test('history reports request errors instead of an empty purchase history', async ({ page }) => {
  await page.route('**/api/purchases?*', route => route.fulfill({ status: 503, json: { detail: 'Database unavailable' } }))
  await page.goto('/history')
  await expect(page.getByRole('alert')).toContainText('Database unavailable')
  await expect(page.getByText('No receipts yet')).toHaveCount(0)
})

test('camera stream is attached after the video mounts', async ({ page }) => {
  await page.addInitScript(() => {
    const canvas = document.createElement('canvas')
    const stream = canvas.captureStream()
    Object.defineProperty(navigator, 'mediaDevices', { value: { getUserMedia: async () => stream } })
    window.BarcodeDetector = class { async detect() { return [] } }
  })
  await page.goto('/manual')
  await page.getByRole('button', { name: 'Scan', exact: false }).click()
  await expect(page.locator('video')).toBeVisible()
  expect(await page.locator('video').evaluate(video => video.srcObject instanceof MediaStream)).toBe(true)
  await page.getByRole('button', { name: 'Stop', exact: false }).click()
  await expect(page.locator('video')).toHaveCount(0)
})
