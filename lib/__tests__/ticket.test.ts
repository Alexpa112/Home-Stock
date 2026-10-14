import { cantidadDudosa, motivoDeDuda, textoCantidad, formatearNumero, esFalloDeRed, PESO_MAXIMO_PLAUSIBLE, precioUnitarioDe } from '../ticket'

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

describe('esFalloDeRed', () => {
  it('reconoce los textos crudos del navegador', () => {
    expect(esFalloDeRed('Failed to fetch')).toBe(true)
    expect(esFalloDeRed('Load failed')).toBe(true)
    expect(esFalloDeRed('NetworkError when attempting to fetch resource.')).toBe(true)
  })
  it('reconoce los 5xx de proxy sin cuerpo util', () => {
    expect(esFalloDeRed('Error HTTP 502')).toBe(true)
    expect(esFalloDeRed('Error HTTP 524')).toBe(true)
  })
  it('no confunde un mensaje real del servidor', () => {
    expect(esFalloDeRed('Archivo demasiado grande (máx 10MB)')).toBe(false)
    expect(esFalloDeRed('Error HTTP 400')).toBe(false)
  })
})

describe('motivoDeDuda', () => {
  it('distingue el decimal en unidades del peso desmedido', () => {
    expect(motivoDeDuda(0.85, 'ud')).toBe('decimal_en_unidades')
    expect(motivoDeDuda(100, 'kg')).toBe('peso_muy_alto')
    expect(motivoDeDuda(PESO_MAXIMO_PLAUSIBLE + 1, 'l')).toBe('peso_muy_alto')
  })
  it('no marca pesos normales ni el limite exacto', () => {
    expect(motivoDeDuda(1.1, 'kg')).toBeNull()
    expect(motivoDeDuda(PESO_MAXIMO_PLAUSIBLE, 'kg')).toBeNull()
    expect(motivoDeDuda(24, 'ud')).toBeNull()
  })
  it('un peso alto sigue contando como dudoso para cantidadDudosa', () => {
    expect(cantidadDudosa(100, 'kg')).toBe(true)
  })
})

describe('precioUnitarioDe', () => {
  it('usa el unitario impreso si lo hay', () => {
    expect(precioUnitarioDe({ precio_unitario: 1.89, precio_total: 1.61 }, 0.85)).toBe(1.89)
  })
  it('deriva el unitario del importe y la cantidad cuando no hay unitario', () => {
    expect(precioUnitarioDe({ precio_unitario: 0, precio_total: 3.7 }, 2)).toBe(1.85)
  })
  it('usa la cantidad corregida por el usuario', () => {
    expect(precioUnitarioDe({ precio_total: 2.2 }, 4)).toBe(0.55)
  })
  it('devuelve undefined si no hay dato fiable', () => {
    expect(precioUnitarioDe({}, 1)).toBeUndefined()
    expect(precioUnitarioDe({ precio_total: 2 }, '')).toBeUndefined()
    expect(precioUnitarioDe({ precio_total: 2 }, 0)).toBeUndefined()
    expect(precioUnitarioDe({ precio_unitario: NaN, precio_total: 0 }, 1)).toBeUndefined()
  })
})
