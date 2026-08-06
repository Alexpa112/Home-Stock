/** Tests de las agregaciones puras usadas por el rediseño de gastos
 * (docs/REDISENO_GASTOS.md, Fase 1). Corren con `npm run test:lib`
 * (ver jest.config.lib.js), separado de los tests JS legacy de
 * stockhogar/static que usa jest.config.js. */
import {
  agruparPorMes,
  totalMes,
  variacionMensual,
  parteDeUsuario,
} from '../gastosStats'

// La simplificación de deudas (sugerir quién paga a quién) vive en el
// backend (GET /api/gastos/simplificar, stockhogar/rutas/gastos.py) y ya
// tiene su propia cobertura ahí; no se duplica esa lógica en el cliente.

describe('agruparPorMes', () => {
  const gastos = [
    { fecha: '2026-11-12', importe_total: 86.4 },
    { fecha: '2026-11-09', importe_total: 64 },
    { fecha: '2026-10-05', importe_total: 72 },
  ]

  it('agrupa por mes y suma el total de cada grupo', () => {
    const grupos = agruparPorMes(gastos)
    expect(grupos).toHaveLength(2)
    expect(grupos[0]).toMatchObject({ ym: '2026-11', total: 150.4 })
    expect(grupos[0].gastos).toHaveLength(2)
    expect(grupos[1]).toMatchObject({ ym: '2026-10', total: 72 })
  })

  it('ordena los meses de más reciente a más antiguo', () => {
    const grupos = agruparPorMes(gastos)
    expect(grupos.map((g) => g.ym)).toEqual(['2026-11', '2026-10'])
  })

  it('con lista vacía no devuelve grupos', () => {
    expect(agruparPorMes([])).toEqual([])
  })
})

describe('totalMes', () => {
  const gastos = [
    { fecha: '2026-11-12', importe_total: 86.4 },
    { fecha: '2026-11-09', importe_total: 64 },
    { fecha: '2026-10-05', importe_total: 72 },
  ]

  it('suma solo los gastos del mes indicado', () => {
    expect(totalMes(gastos, '2026-11')).toBeCloseTo(150.4, 2)
  })

  it('devuelve 0 para un mes sin gastos', () => {
    expect(totalMes(gastos, '2026-01')).toBe(0)
  })
})

describe('variacionMensual', () => {
  const gastos = [
    { fecha: '2026-11-01', importe_total: 110 },
    { fecha: '2026-10-01', importe_total: 100 },
  ]

  it('calcula el porcentaje de variación frente al mes anterior', () => {
    expect(variacionMensual(gastos, '2026-11', '2026-10')).toBe(10)
  })

  it('devuelve null si el mes anterior no tiene gastos', () => {
    expect(variacionMensual(gastos, '2026-11', '2025-01')).toBeNull()
  })
})

describe('parteDeUsuario', () => {
  const gasto = {
    fecha: '2026-11-12',
    importe_total: 86.4,
    participantes: [
      { usuario_id: 1, importe: 28.8 },
      { usuario_id: 2, importe: 57.6 },
    ],
  }

  it('devuelve el importe del participante indicado', () => {
    expect(parteDeUsuario(gasto, 1)).toBe(28.8)
  })

  it('devuelve 0 si el usuario no participa en el gasto', () => {
    expect(parteDeUsuario(gasto, 99)).toBe(0)
  })

  it('devuelve 0 si no hay usuario actual (usuarioId null)', () => {
    expect(parteDeUsuario(gasto, null)).toBe(0)
  })
})
