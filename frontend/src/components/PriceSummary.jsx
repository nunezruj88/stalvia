export default function PriceSummary({ summary }) {
  return <section className="bg-white border rounded-xl p-5 space-y-3">
    <h2 className="font-bold">Cobertura de la comparación</h2>
    <p>Solo se comparan cestas completas con todas las coincidencias confirmadas. Confirma el mismo producto, formato y unidad de venta; no confirmes un envase frente a un precio por kg.</p>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {Object.entries(summary.totals_by_super).map(([s, total]) => <div className="border rounded p-3" key={s}>
        <strong>{s}</strong><p>{summary.coverage[s]} / {summary.product_count} confirmados</p>
        <p>{total == null ? 'Cesta incompleta' : `${total.toFixed(2)} €`}</p>
      </div>)}
    </div>
    {summary.cheapest_supermarket && <p>Menor total confirmado: {summary.cheapest_supermarket}. Ahorro estimado: {summary.potential_savings.toFixed(2)} €.</p>}
  </section>
}
