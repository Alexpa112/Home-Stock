import { nombreCategoriaGasto } from '../categoriasGasto'

const ingles: Record<string, string> = {
  catgasto_alimentacion: 'Food',
  catgasto_transporte: 'Transport',
  catgasto_vivienda: 'Housing',
  catgasto_ocio: 'Leisure',
  catgasto_salud: 'Health',
  catgasto_suministros: 'Utilities',
  catgasto_otros: 'Other',
}
const t = (clave: string) => ingles[clave] ?? clave

describe('nombreCategoriaGasto', () => {
  it('traduce las siete categorias por defecto', () => {
    expect(nombreCategoriaGasto('Alimentación', t)).toBe('Food')
    expect(nombreCategoriaGasto('Transporte', t)).toBe('Transport')
    expect(nombreCategoriaGasto('Vivienda', t)).toBe('Housing')
    expect(nombreCategoriaGasto('Ocio', t)).toBe('Leisure')
    expect(nombreCategoriaGasto('Salud', t)).toBe('Health')
    expect(nombreCategoriaGasto('Suministros', t)).toBe('Utilities')
    expect(nombreCategoriaGasto('Otros', t)).toBe('Other')
  })

  it('una categoria propia del usuario se muestra tal cual', () => {
    expect(nombreCategoriaGasto('Mascotas del piso', t)).toBe('Mascotas del piso')
    expect(nombreCategoriaGasto('', t)).toBe('')
  })

  it('en espanol queda igual', () => {
    const es = (clave: string) => ({ catgasto_ocio: 'Ocio' } as Record<string, string>)[clave] ?? clave
    expect(nombreCategoriaGasto('Ocio', es)).toBe('Ocio')
  })
})
