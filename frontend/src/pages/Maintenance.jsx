import { useEffect, useRef, useState } from 'react'
import Manual from './Manual'
import ComparisonTable from '../components/ComparisonTable'
import { getCatalog, compareProduct } from '../services/api'

const LABELS = { mercadona: 'Mercadona', carrefour: 'Carrefour', bonpreu: 'Bonpreu / Esclat', elcorteingles: 'El Corte Inglés', alcampo: 'Alcampo' }
const PAGE_SIZE = 25
const money = n => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n)
const observed = value => new Date(value.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`).toLocaleDateString('es-ES')

export default function Maintenance() {
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(0)
  const [catalog, setCatalog] = useState({ products: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [showForm, setShowForm] = useState(false)
  const [notice, setNotice] = useState('')
  const [selected, setSelected] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [comparing, setComparing] = useState(false)
  const [compareError, setCompareError] = useState('')
  const detailRef = useRef(null)
  useEffect(() => { if (selected) detailRef.current?.focus() }, [selected?.id])
  const request = useRef(0)
  useEffect(() => () => { request.current += 1 }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    getCatalog(query, page * PAGE_SIZE, PAGE_SIZE, controller.signal)
      .then(data => { if (!controller.signal.aborted) setCatalog(data) })
      .catch(e => { if (!controller.signal.aborted) setError(e.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [query, page, refresh])

  const choose = product => {
    request.current += 1
    setSelected(product); setComparison(null); setComparing(false); setCompareError('')
  }
  const saved = product => {
    setNotice(`«${product.canonical_name}» guardado. Puedes consultarlo en el catálogo y comparar sus precios.`)
    setShowForm(false); setSearch(product.canonical_name); setQuery(product.canonical_name); setPage(0)
    setRefresh(n => n + 1); choose(null)
  }
  const compare = async () => {
    const id = ++request.current
    setComparing(true); setCompareError(''); setComparison(null)
    try {
      const result = await compareProduct({ raw_name: selected.canonical_name, canonical_name: selected.canonical_name, barcode: selected.barcode || '', quantity: '1', unit_price: '0', total_price: '0' })
      if (id === request.current) setComparison(result)
    } catch (e) { if (id === request.current) setCompareError(e.message) }
    finally { if (id === request.current) setComparing(false) }
  }
  const confirm = (_, store, comparable) => setComparison(p => ({ ...p, prices: { ...p.prices, [store]: { ...p.prices[store], comparable } } }))
  const confirmed = Object.entries(comparison?.prices || {}).filter(([, p]) => p?.comparable && Number(p.price) > 0).sort((a, b) => Number(a[1].price) - Number(b[1].price))

  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h1 className="text-2xl font-bold">Mantenimiento</h1><p className="text-slate-500 mt-1">Productos guardados y precios registrados.</p></div>
      <button className="bg-green-700 text-white rounded-xl px-4 py-2" onClick={() => setShowForm(v => !v)}>{showForm ? 'Cerrar alta manual' : '+ Nuevo producto'}</button>
    </div>
    {notice && <p role="status" className="bg-green-50 text-green-900 p-4 rounded-xl">{notice}</p>}
    {showForm && <Manual onSaved={saved} />}
    <form className="flex flex-wrap gap-2" onSubmit={e => { e.preventDefault(); setQuery(search.trim()); setPage(0); setRefresh(n => n + 1); choose(null) }}>
      <input aria-label="Buscar por nombre o código de barras" className="min-w-0 flex-1 border rounded-xl p-3" maxLength={250} placeholder="Nombre o código de barras" value={search} onChange={e => setSearch(e.target.value)} />
      <button className="border bg-white rounded-xl px-4 py-2">Buscar</button>
    </form>
    {loading ? <p role="status">Cargando productos…</p> : error ? <div role="alert" className="bg-red-50 p-4 rounded-xl">{error}<button className="ml-3 underline" onClick={() => setRefresh(n => n + 1)}>Reintentar</button></div> : <>
      <p className="text-sm text-slate-500">{catalog.total} productos encontrados</p>
      {!catalog.products.length && <div className="bg-white border rounded-xl p-8 text-center">{query ? 'No hay productos que coincidan con la búsqueda.' : 'Todavía no hay productos guardados. Añade el primero con «Nuevo producto».'}</div>}
      <div className="grid sm:grid-cols-2 gap-3">{catalog.products.map(product => <article className="bg-white border rounded-xl p-4 space-y-2 min-w-0" key={product.id}>
        <h2 className="font-semibold break-words">{product.canonical_name}</h2>
        <p className="text-sm text-slate-500">{product.barcode || 'Sin código de barras'}{product.category ? ` · ${product.category}` : ''}</p>
        <p className="text-sm">Precios en {Object.keys(product.latest_prices).length} supermercados</p>
        <button className="text-green-800 underline" onClick={() => choose(product)}>Ver precios y comparar<span className="sr-only"> {product.canonical_name}</span></button>
      </article>)}</div>
      {catalog.total > PAGE_SIZE && <div className="flex items-center justify-between gap-3">
        <button disabled={page === 0} className="border rounded px-3 py-2 disabled:opacity-40" onClick={() => setPage(p => p - 1)}>Anterior</button>
        <span>Página {page + 1} de {Math.ceil(catalog.total / PAGE_SIZE)}</span>
        <button disabled={(page + 1) * PAGE_SIZE >= catalog.total} className="border rounded px-3 py-2 disabled:opacity-40" onClick={() => setPage(p => p + 1)}>Siguiente</button>
      </div>}
    </>}
    {selected && <section ref={detailRef} tabIndex={-1} className="bg-white border rounded-xl p-5 space-y-4 scroll-mt-20" aria-label="Detalle del producto">
      <div className="flex justify-between gap-3"><h2 className="font-bold text-lg">{selected.canonical_name}</h2><button className="underline" onClick={() => choose(null)}>Cerrar detalle</button></div>
      <h3 className="font-semibold">Últimos precios guardados</h3>
      <p className="text-sm text-slate-500">Son observaciones guardadas, no precios consultados en este momento. Comprueba la fecha y el formato.</p>
      <div className="grid sm:grid-cols-2 gap-2">{Object.entries(LABELS).map(([store, label]) => {
        const price = selected.latest_prices[store]
        return <div className="border rounded-lg p-3" key={store}><strong>{label}</strong>{price ? <><p>{money(price.price)}</p><p className="text-xs text-slate-500">{observed(price.observed_at)} · {price.source === 'manual' ? 'Alta manual' : price.source === 'receipt' ? 'Ticket' : price.source}</p></> : <p className="text-slate-500">Sin precio guardado</p>}</div>
      })}</div>
      <button disabled={comparing} className="bg-green-700 text-white rounded-xl px-4 py-2 disabled:opacity-50" onClick={compare}>{comparing ? 'Consultando supermercados…' : 'Comparar precios en supermercados'}</button>
      <p className="text-sm text-slate-500">La búsqueda es opcional. Las coincidencias deben corresponder al mismo producto y formato.</p>
      {compareError && <p role="alert" className="text-red-700">{compareError}</p>}
      {comparison && <><p role="status">Consulta terminada. Confirma las coincidencias para comparar.</p>
        {confirmed.length >= 2 && <p className="bg-green-50 p-3 rounded-lg">Menor precio confirmado: {LABELS[confirmed[0][0]]}, {money(confirmed[0][1].price)} por unidad de venta.</p>}
        <ComparisonTable products={[comparison]} onConfirm={confirm} showPaid={false} />
      </>}
    </section>}
  </div>
}
