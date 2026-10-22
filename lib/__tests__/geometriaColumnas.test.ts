import { geometriaColumnas, MINIMO_COLUMNAS } from '../geometriaColumnas'

describe('geometriaColumnas', () => {
  it('un solo dato no ocupa todo el ancho', () => {
    const { anchoCol, desplazamiento } = geometriaColumnas(1)
    expect(anchoCol).toBeCloseTo(100 / MINIMO_COLUMNAS)
    expect(anchoCol * 0.7).toBeLessThan(15)
    expect(desplazamiento).toBeCloseTo((100 - anchoCol) / 2)
  })

  it('el grupo queda centrado', () => {
    const { anchoCol, desplazamiento } = geometriaColumnas(3)
    expect(desplazamiento * 2 + anchoCol * 3).toBeCloseTo(100)
  })

  it('con muchos datos reparte todo el ancho sin desplazamiento', () => {
    const { anchoCol, desplazamiento } = geometriaColumnas(12)
    expect(anchoCol).toBeCloseTo(100 / 12)
    expect(desplazamiento).toBeCloseTo(0)
  })

  it('con cero datos no divide entre cero', () => {
    const { anchoCol, desplazamiento } = geometriaColumnas(0)
    expect(Number.isFinite(anchoCol)).toBe(true)
    expect(desplazamiento).toBeCloseTo(50)
  })
})
