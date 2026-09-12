import { useState } from 'react'
import { analyzeTicket, saveReceipt, compareProduct } from '../services/api'
import ComparisonTable from '../components/ComparisonTable'
import PriceSummary from '../components/PriceSummary'
import { summarize } from '../services/comparison'

export default function Home() {
  const [draft, setDraft] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [products, setProducts] = useState([])
  const [saved, setSaved] = useState(false)
  const process = async file => {
    if (!file || busy) return
    if (file.size > 8 * 1024 * 1024) { setError('La imagen supera 8 MB'); return }
    setDraft(null); setBusy(true); setError(''); setMessage('Leyendo ticket…'); setProducts([]); setSaved(false)
    try {
      const { warnings, ...receipt } = await analyzeTicket(file)
      setDraft(receipt); setMessage(warnings.join(' '))
    } catch (e) { setError(e.message); setMessage('') }
    finally { setBusy(false) }
  }
  const change = (index, field, value) => setDraft(d => ({ ...d, products: d.products.map((p, i) => i === index ? { ...p, [field]: value } : p) }))
  const save = async event => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const result = await saveReceipt(draft)
      setSaved(true)
      setMessage(result.duplicate ? 'Este ticket ya estaba guardado.' : 'Ticket guardado. Ya puedes buscar precios.')
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  const compare = async () => {
    setBusy(true); setError(''); setProducts([])
    try {
      for (const [i, product] of draft.products.entries()) {
        setMessage(`Buscando producto ${i + 1} de ${draft.products.length}…`)
        const result = await compareProduct(product)
        setProducts(previous => [...previous, result])
      }
      setMessage('Búsqueda completada. Confirma solo coincidencias del mismo producto y formato.')
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  const confirm = (index, store, checked) => setProducts(rows => rows.map((p, i) => i === index ? { ...p, prices: { ...p.prices, [store]: { ...p.prices[store], comparable: checked } } } : p))
  return <div className="space-y-5">
    <h1 className="text-2xl font-bold">Revisar un ticket</h1>
    <label className="block bg-white border rounded-xl p-6">Foto JPEG, PNG o WebP (máximo 8 MB)
      <input aria-label="Foto del ticket" className="block mt-3" type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={e => process(e.target.files[0])} />
    </label>
    {message && <p role="status">{message}</p>}
    {error && <p role="alert" className="bg-red-50 text-red-800 p-4 rounded-xl">{error}</p>}
    {draft && <form onSubmit={save} className="bg-white border rounded-xl p-5 space-y-4">
      <p>Corrige nombres, cantidades y totales antes de guardar. Los descuentos se conservan en el total de cada línea.</p>
      <fieldset disabled={busy || saved} className="space-y-4">
        <div className="flex gap-3 flex-wrap">
          <label>Supermercado<select className="block border rounded p-2" value={draft.supermarket} onChange={e => setDraft({ ...draft, supermarket: e.target.value })}>
            {['unknown','mercadona','carrefour','bonpreu','elcorteingles','alcampo'].map(s => <option key={s}>{s}</option>)}
          </select></label>
          <label>Fecha<input className="block border rounded p-2" required type="date" value={draft.date || ''} onChange={e => setDraft({ ...draft, date: e.target.value })} /></label>
          <label>Total (€)<input className="block border rounded p-2" required type="number" min="0" step="0.01" value={draft.total} onChange={e => setDraft({ ...draft, total: e.target.value })} /></label>
        </div>
        {draft.products.map((p, i) => <div className="border-t pt-3 grid grid-cols-2 md:grid-cols-5 gap-2" key={i}>
          <label className="col-span-2 md:col-span-1">Producto<input aria-label={`Producto ${i + 1}`} className="w-full border rounded p-2" required value={p.canonical_name} onChange={e => change(i, 'canonical_name', e.target.value)} /></label>
          <label>Cantidad<input className="w-full border rounded p-2" required type="number" min="0.0001" step="0.0001" value={p.quantity} onChange={e => change(i, 'quantity', e.target.value)} /></label>
          <label>Precio unitario<input className="w-full border rounded p-2" required type="number" min="0" step="0.01" value={p.unit_price} onChange={e => change(i, 'unit_price', e.target.value)} /></label>
          <label>Total línea<input className="w-full border rounded p-2" required type="number" min="0" step="0.01" value={p.total_price} onChange={e => change(i, 'total_price', e.target.value)} /></label>
          <label>Código de barras<input className="w-full border rounded p-2" value={p.barcode} onChange={e => change(i, 'barcode', e.target.value)} /></label>
          <button className="text-red-700 underline text-left" type="button" onClick={() => setDraft(d => ({ ...d, products: d.products.filter((_, index) => index !== i) }))}>Eliminar línea {i + 1}</button>
        </div>)}
        <button className="border rounded px-3 py-2 mr-3" type="button" onClick={() => setDraft(d => ({ ...d, products: [...d.products, { raw_name: 'Añadido manualmente', canonical_name: '', quantity: '1', unit_price: '0.00', total_price: '0.00', barcode: '' }] }))}>Añadir línea</button>
        <button className="bg-green-700 text-white rounded px-4 py-2 disabled:opacity-50" type="submit">Confirmar y guardar</button>
      </fieldset>
      {saved && <button className="bg-green-700 text-white rounded px-4 py-2 disabled:opacity-50" type="button" disabled={busy} onClick={compare}>Buscar precios</button>}
    </form>}
    {!!products.length && <>
      <PriceSummary summary={summarize(products, draft.products.length)} />
      <ComparisonTable products={products} onConfirm={confirm} />
    </>}
  </div>
}
