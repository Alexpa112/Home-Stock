import { cantidadDudosa, textoCantidad, formatearNumero } from '../ticket'

describe('cantidadDudosa', () => {
  it('marca un decimal con unidad ud (el caso del tomate pera)', () => {
    expect(cantidadDudosa(0.85, 'ud')).toBe(true)
    expect(cantidadDudosa(1.5, 'UD')).toBe(true)
  })
  it('no marca enteros con ud', () => {
    expect(cantidadDudosa(3, 'ud')).toBe(false)
    expect(cantidadDudosa(1, 'ud')).toBe(false)
  })
  it('no marca decimales legítimos de peso o volumen', () => {
    expect(cantidadDudosa(0.85, 'kg')).toBe(false)
    expect(cantidadDudosa(0.5, 'l')).toBe(false)
  })
  it('no marca el campo vacío ni valores no numéricos', () => {
    expect(cantidadDudosa('', 'ud')).toBe(false)
    expect(cantidadDudosa(NaN, 'ud')).toBe(false)
  })
})

describe('textoCantidad', () => {
  it('formatea unidades como ×n y pesos con su unidad', () => {
    expect(textoCantidad(3, 'ud', 'es-ES')).toBe('×3')
    expect(textoCantidad(0.85, 'kg', 'es-ES')).toBe('0,85 kg')
    expect(textoCantidad(0.85, 'kg', 'en-US')).toBe('0.85 kg')
  })
  it('devuelve vacío si no hay cantidad', () => {
    expect(textoCantidad('', 'ud')).toBe('')
  })
})

describe('formatearNumero', () => {
  it('usa el separador del idioma indicado y recorta a 3 decimales', () => {
    expect(formatearNumero(0.85, 'es-ES')).toBe('0,85')
    expect(formatearNumero(1.23456, 'en-US')).toBe('1.235')
  })
})
