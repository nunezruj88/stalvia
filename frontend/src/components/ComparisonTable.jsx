import { STORES } from '../services/comparison'
export default function ComparisonTable({ products, onConfirm }) {
  return <div className="space-y-4">{products.map((p, i) => <section className="bg-white border rounded-xl p-5" key={i}>
    <h3 className="font-bold">{p.canonical_name} × {p.quantity}</h3>
    <p className="text-sm mb-3">Pagado por esta línea: {Number(p.total_price).toFixed(2)} €</p>
    <div className="grid md:grid-cols-2 gap-3">{STORES.map(store => {
      const item = p.prices?.[store]
      const found = Number(item?.price) > 0
      const safeUrl = item?.url?.startsWith('https://') ? item.url : null
      return <div key={store} className="border rounded p-3">
        <strong>{store}</strong>
        {found ? <><p>{item.name}: {Number(item.price).toFixed(2)} €</p>
          {safeUrl && <a className="underline text-green-800" href={safeUrl} target="_blank" rel="noreferrer">Ver producto y formato</a>}
          <p className="text-xs">Consulta: {item.observed_at ? new Date(item.observed_at).toLocaleString() : 'sin fecha'}</p>
          <label className="block mt-2"><input type="checkbox" checked={!!item.comparable} onChange={e => onConfirm(i, store, e.target.checked)} /> He comprobado que coincide el producto, formato y unidad</label>
        </> : <p>{item?.status === 'error' ? 'No se pudo consultar esta tienda' : 'Precio no disponible'}</p>}
      </div>
    })}</div>
  </section>)}</div>
}
