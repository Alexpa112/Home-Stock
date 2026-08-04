/** Agregaciones puras para las estadísticas de gastos compartidos (ver
 * app/dashboard/gastos/page.tsx). Se calculan en memoria a partir de los
 * gastos ya cargados, sin necesidad de un endpoint de agregación aparte. */

export interface DatoBarra {
  etiqueta: string
  valor: number
}

interface GastoConCategoriaYFecha {
  importe_total: number
  categoria?: string | null
  fecha: string
}

interface SaldoItemLike {
  nombre_usuario: string
  saldo: number
}

/** Suma importe_total agrupado por categoría (o el bucket de "sin categoría"), orden descendente. */
export function totalesPorCategoria(
  gastos: GastoConCategoriaYFecha[],
  etiquetaSinCategoria: string
): DatoBarra[] {
  const mapa = new Map<string, number>()
  for (const g of gastos) {
    const clave = g.categoria || etiquetaSinCategoria
    mapa.set(clave, (mapa.get(clave) ?? 0) + g.importe_total)
  }
  return Array.from(mapa, ([etiqueta, valor]) => ({ etiqueta, valor })).sort((a, b) => b.valor - a.valor)
}

/** Serie de los últimos `meses` meses (incluye el actual), en orden cronológico, con 0 en los meses sin gasto. */
export function evolucionMensual(gastos: GastoConCategoriaYFecha[], meses = 12): DatoBarra[] {
  const hoy = new Date()
  const claves: string[] = []
  for (let i = meses - 1; i >= 0; i--) {
    const d = new Date(hoy.getFullYear(), hoy.getMonth() - i, 1)
    claves.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }
  const totales = new Map(claves.map((c) => [c, 0]))
  for (const g of gastos) {
    const clave = (g.fecha || '').slice(0, 7)
    if (totales.has(clave)) totales.set(clave, (totales.get(clave) ?? 0) + g.importe_total)
  }
  return claves.map((c) => ({ etiqueta: `${c.slice(5)}/${c.slice(2, 4)}`, valor: totales.get(c) ?? 0 }))
}

/** Reutiliza el saldo ya calculado por el backend (GET /api/gastos/saldo). */
export function balancePorPersona(saldo: SaldoItemLike[]): DatoBarra[] {
  return saldo.map((s) => ({ etiqueta: s.nombre_usuario, valor: s.saldo }))
}
