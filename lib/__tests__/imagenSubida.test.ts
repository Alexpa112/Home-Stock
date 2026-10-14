import {
  debeReducirse, dimensionesObjetivo, UMBRAL_REDUCIR_BYTES, MAX_PIXELES,
} from '../imagenSubida'

describe('debeReducirse', () => {
  it('solo reduce imagenes que pasan del umbral', () => {
    expect(debeReducirse('image/jpeg', UMBRAL_REDUCIR_BYTES + 1)).toBe(true)
    expect(debeReducirse('image/jpeg', UMBRAL_REDUCIR_BYTES)).toBe(false)
    expect(debeReducirse('image/png', 12 * 1024 * 1024)).toBe(true)
  })
  it('no toca PDF ni HEIC (el navegador no los decodifica de forma fiable)', () => {
    expect(debeReducirse('application/pdf', 50 * 1024 * 1024)).toBe(false)
    expect(debeReducirse('image/heic', 50 * 1024 * 1024)).toBe(false)
    expect(debeReducirse('', 50 * 1024 * 1024)).toBe(false)
  })
})

describe('dimensionesObjetivo', () => {
  it('no cambia lo que ya cabe', () => {
    expect(dimensionesObjetivo(3000, 2000)).toEqual({ ancho: 3000, alto: 2000 })
  })
  it('reduce una foto de 50 MP conservando la proporcion', () => {
    const r = dimensionesObjetivo(8000, 6000)
    expect(r.ancho * r.alto).toBeLessThanOrEqual(MAX_PIXELES * 1.001)
    expect(Math.abs(r.ancho / r.alto - 8000 / 6000)).toBeLessThan(0.01)
  })
  it('un ticket largo y estrecho no pierde anchura util', () => {
    // 1500x6000 = 9 MP: solo se recorta un 6 %, no se queda en 800 px de ancho
    const r = dimensionesObjetivo(1500, 6000)
    expect(r.ancho).toBeGreaterThan(1400)
  })
})
