import { sinTildes, filtrarPorNombre } from '../texto'

describe('sinTildes', () => {
  it('quita tildes y pasa a minúsculas', () => {
    expect(sinTildes('Plátano')).toBe('platano')
    expect(sinTildes('CHAMPÚ')).toBe('champu')
    expect(sinTildes('Jamón Serrano')).toBe('jamon serrano')
  })

  it('deja intacto lo que no lleva tildes', () => {
    expect(sinTildes('pan')).toBe('pan')
  })

  it('la ñ tambien se reduce a n, a proposito', () => {
    // NFD descompone la ñ en n + tilde, asi que acaba en "n". Para un buscador
    // es lo que interesa: quien escribe "pina" o "panal" desde el movil espera
    // encontrar "Piña" y "Pañal".
    expect(sinTildes('Piña')).toBe('pina')
  })
})

describe('filtrarPorNombre', () => {
  const catalogo = [
    { nombre: 'Plátano' },
    { nombre: 'Pan de molde' },
    { nombre: 'Champú anticaída' },
    { nombre: 'Leche entera' },
  ]

  it('encuentra aunque el usuario escriba sin tildes', () => {
    expect(filtrarPorNombre(catalogo, 'platano').map((a) => a.nombre)).toEqual(['Plátano'])
    expect(filtrarPorNombre(catalogo, 'champu').map((a) => a.nombre)).toEqual(['Champú anticaída'])
  })

  it('ignora mayúsculas y espacios sobrantes', () => {
    expect(filtrarPorNombre(catalogo, '  LECHE  ').map((a) => a.nombre)).toEqual(['Leche entera'])
  })

  it('busca por cualquier parte del nombre, no solo por el principio', () => {
    expect(filtrarPorNombre(catalogo, 'molde').map((a) => a.nombre)).toEqual(['Pan de molde'])
  })

  it('con la consulta vacía devuelve todo', () => {
    expect(filtrarPorNombre(catalogo, '')).toHaveLength(4)
    expect(filtrarPorNombre(catalogo, '   ')).toHaveLength(4)
  })

  it('devuelve lista vacía si no hay coincidencias', () => {
    expect(filtrarPorNombre(catalogo, 'zzz')).toEqual([])
  })
})
