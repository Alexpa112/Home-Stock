import { epigrafeAntesDe } from '../agruparAcciones'

describe('epigrafeAntesDe', () => {
  const acciones = [
    { grupo: 'Esta pantalla' },
    { grupo: 'Esta pantalla' },
    { grupo: 'Ir a' },
    { grupo: 'Ir a' },
  ]

  it('pinta el epígrafe solo en la primera acción de cada grupo', () => {
    expect(acciones.map((_, i) => epigrafeAntesDe(acciones, i))).toEqual([
      'Esta pantalla',
      undefined,
      'Ir a',
      undefined,
    ])
  })

  it('no pinta nada si la acción no tiene grupo', () => {
    expect(epigrafeAntesDe([{}, {}], 0)).toBeUndefined()
  })

  it('un grupo que reaparece tras otro vuelve a llevar epígrafe', () => {
    const a = [{ grupo: 'A' }, { grupo: 'B' }, { grupo: 'A' }]
    expect(epigrafeAntesDe(a, 2)).toBe('A')
  })
})
