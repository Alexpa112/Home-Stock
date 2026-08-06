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

interface ParticipanteLike {
  usuario_id: number
  importe: number
}

interface GastoConParticipantes {
  fecha: string
  importe_total: number
  participantes: ParticipanteLike[]
}

export interface GrupoMes<T> {
  ym: string // "2026-11", para ordenar y para formatear con Intl.DateTimeFormat en el componente
  total: number
  gastos: T[]
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

/** Agrupa gastos por mes (según `fecha`), más reciente primero. La
 * etiqueta legible (p. ej. "noviembre de 2026") se deja al componente vía
 * Intl.DateTimeFormat con el idioma activo, para no fijar aquí un idioma. */
export function agruparPorMes<T extends { fecha: string; importe_total: number }>(
  gastos: T[]
): GrupoMes<T>[] {
  const grupos = new Map<string, GrupoMes<T>>()
  for (const g of gastos) {
    const ym = (g.fecha || '').slice(0, 7)
    let grupo = grupos.get(ym)
    if (!grupo) {
      grupo = { ym, total: 0, gastos: [] }
      grupos.set(ym, grupo)
    }
    grupo.total += g.importe_total
    grupo.gastos.push(g)
  }
  return Array.from(grupos.values()).sort((a, b) => b.ym.localeCompare(a.ym))
}

/** Suma de importe_total de los gastos cuya fecha cae en el mes `ym` ("2026-11"). */
export function totalMes(gastos: { fecha: string; importe_total: number }[], ym: string): number {
  return gastos
    .filter((g) => (g.fecha || '').slice(0, 7) === ym)
    .reduce((acc, g) => acc + g.importe_total, 0)
}

/** Variación porcentual del total de `ymActual` frente a `ymAnterior`.
 * `null` cuando no hay datos del mes anterior con los que comparar. */
export function variacionMensual(
  gastos: { fecha: string; importe_total: number }[],
  ymActual: string,
  ymAnterior: string
): number | null {
  const actual = totalMes(gastos, ymActual)
  const anterior = totalMes(gastos, ymAnterior)
  if (anterior <= 0) return null
  return Math.round(((actual - anterior) / anterior) * 1000) / 10
}

/** Importe que le corresponde a `usuarioId` dentro de un gasto (0 si no participa). */
export function parteDeUsuario(gasto: GastoConParticipantes, usuarioId: number | null): number {
  if (usuarioId === null) return 0
  return gasto.participantes.find((p) => p.usuario_id === usuarioId)?.importe ?? 0
}
