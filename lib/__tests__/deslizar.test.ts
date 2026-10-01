import {
  clasificarMovimiento, desplazamientoVisible, gestoCompleto, empiezaEnElBorde,
  UMBRAL_MOVIMIENTO, UMBRAL_COMPLETA, DESPLAZAMIENTO_MAXIMO, MARGEN_BORDE,
} from '../deslizar'

describe('clasificarMovimiento', () => {
  it('por debajo de 8 px sigue siendo una pulsación', () => {
    expect(clasificarMovimiento(UMBRAL_MOVIMIENTO - 1, 0)).toBe('pendiente')
    expect(clasificarMovimiento(3, -5)).toBe('pendiente')
  })
  it('a partir de 8 px decide por el eje dominante', () => {
    expect(clasificarMovimiento(UMBRAL_MOVIMIENTO, 0)).toBe('horizontal')
    expect(clasificarMovimiento(-20, 5)).toBe('horizontal')
    expect(clasificarMovimiento(5, 20)).toBe('vertical')
  })
  it('una diagonal exacta se trata como scroll (vertical)', () => {
    expect(clasificarMovimiento(15, 15)).toBe('vertical')
  })
})

describe('desplazamientoVisible', () => {
  it('no se mueve hacia la izquierda', () => {
    expect(desplazamientoVisible(-40)).toBe(0)
  })
  it('sigue al dedo y se detiene en el máximo', () => {
    expect(desplazamientoVisible(50)).toBe(50)
    expect(desplazamientoVisible(500)).toBe(DESPLAZAMIENTO_MAXIMO)
  })
})

describe('gestoCompleto', () => {
  it('exige llegar al umbral', () => {
    expect(gestoCompleto(UMBRAL_COMPLETA - 1)).toBe(false)
    expect(gestoCompleto(UMBRAL_COMPLETA)).toBe(true)
    expect(gestoCompleto(-200)).toBe(false)
  })
})

describe('empiezaEnElBorde', () => {
  it('reserva el borde izquierdo al gesto atrás del sistema', () => {
    expect(empiezaEnElBorde(MARGEN_BORDE - 1)).toBe(true)
    expect(empiezaEnElBorde(MARGEN_BORDE)).toBe(false)
  })
})
