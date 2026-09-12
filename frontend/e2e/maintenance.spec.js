import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('https://fonts.googleapis.com/**', route => route.abort())
  await page.route('https://fonts.gstatic.com/**', route => route.abort())
})


test('catalog, manual creation and optional comparison', async ({ page }) => {
  let products = [{ id: 1, canonical_name: 'Leche entera 1L', barcode: '4006381333931', category: 'dairy', latest_prices: { mercadona: { price: 1.5, observed_at: '2026-09-01T10:00:00', source: 'manual' } } }]
  let comparisons = 0
  await page.route('**/api/catalog?*', route => {
    const query = new URL(route.request().url()).searchParams.get('search')
    const filtered = products.filter(p => !query || p.canonical_name.includes(query) || p.barcode?.includes(query))
    return route.fulfill({ json: { total: filtered.length, products: filtered } })
  })
  await page.route('**/api/products/manual', route => {
    const data = route.request().postDataJSON()
    products = [...products, { id: 2, canonical_name: data.name, barcode: data.barcode, category: data.category, latest_prices: { [data.supermarket]: { price: Number(data.price), observed_at: '2026-09-01T10:00:00', source: 'manual' } } }]
    return route.fulfill({ json: { product_id: 2, canonical_name: data.name, price_saved: true } })
  })
  await page.route('**/api/compare-product', route => {
    comparisons += 1
    return route.fulfill({ json: { ...route.request().postDataJSON(), prices: {
      mercadona: { name: 'Arroz 1kg', price: 1.1, comparable: false },
      carrefour: { name: 'Arroz 1kg', price: 1.2, comparable: false },
    } } })
  })
  await page.goto('/')
  await page.getByRole('link', { name: 'Mantenimiento', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Mantenimiento' })).toBeVisible()
  await page.getByRole('button', { name: 'Ver precios y comparar Leche entera 1L' }).click()
  await expect(page.getByRole('region', { name: 'Detalle del producto' })).toContainText('1,50')
  expect(comparisons).toBe(0)
  await page.getByRole('button', { name: '+ Nuevo producto', exact: true }).click()
  await page.getByLabel('Nombre del producto', { exact: true }).fill('Arroz 1kg')
  await page.getByLabel('Supermercado', { exact: true }).selectOption('mercadona')
  await page.getByLabel('Precio (€)', { exact: true }).fill('1.50')
  await page.getByRole('button', { name: '+ Guardar producto', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Arroz 1kg', exact: true })).toBeVisible()
  expect(comparisons).toBe(0)
  await page.getByRole('button', { name: 'Ver precios y comparar Arroz 1kg' }).click()
  await page.getByRole('button', { name: 'Comparar precios en supermercados', exact: true }).click()
  await expect(page.getByText('Consulta terminada.', { exact: false })).toBeVisible()
  expect(comparisons).toBe(1)
  await expect(page.getByText('Pagado por esta línea:', { exact: false })).toHaveCount(0)
  await page.getByRole('checkbox').nth(0).check()
  await expect(page.getByText('Menor precio confirmado:', { exact: false })).toHaveCount(0)
  await page.getByRole('checkbox').nth(1).check()
  await expect(page.getByText('Menor precio confirmado:', { exact: false })).toContainText('Mercadona')
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 390)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: 'test-results/maintenance-mobile.png', fullPage: true })
})

test('catalog pagination, empty result and retry', async ({ page }) => {
  let failed = true
  await page.route('**/api/catalog?*', route => {
    if (failed) return route.fulfill({ status: 503, json: { detail: 'Catálogo no disponible' } })
    const params = new URL(route.request().url()).searchParams
    const skip = Number(params.get('skip'))
    return route.fulfill({ json: params.get('search') ? { total: 0, products: [] } : { total: 26, products: [{ id: skip + 1, canonical_name: `Producto ${skip + 1}`, barcode: null, latest_prices: {} }] } })
  })
  await page.goto('/mantenimiento')
  await expect(page.getByRole('alert')).toContainText('Catálogo no disponible')
  failed = false
  await page.getByRole('button', { name: 'Reintentar', exact: true }).click()
  await page.getByRole('button', { name: 'Siguiente', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Producto 26', exact: true })).toBeVisible()
  await page.getByLabel('Buscar por nombre o código de barras').fill('No existe')
  await page.getByRole('button', { name: 'Buscar', exact: true }).click()
  await expect(page.getByText('No hay productos que coincidan con la búsqueda.')).toBeVisible()
})
