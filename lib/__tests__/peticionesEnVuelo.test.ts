import { compartirEnVuelo, olvidarEnVuelo } from '../peticionesEnVuelo'

describe('compartirEnVuelo', () => {
  beforeEach(() => olvidarEnVuelo())

  it('las llamadas simultaneas comparten una sola peticion', async () => {
    const peticion = jest.fn(() => new Promise<string>((r) => setTimeout(() => r('datos'), 5)))
    const [a, b, c] = await Promise.all([
      compartirEnVuelo('x', peticion),
      compartirEnVuelo('x', peticion),
      compartirEnVuelo('x', peticion),
    ])
    expect([a, b, c]).toEqual(['datos', 'datos', 'datos'])
    expect(peticion).toHaveBeenCalledTimes(1)
  })

  it('al resolver se olvida: la siguiente lectura pide datos nuevos', async () => {
    let n = 0
    const peticion = () => Promise.resolve(++n)
    expect(await compartirEnVuelo('x', peticion)).toBe(1)
    expect(await compartirEnVuelo('x', peticion)).toBe(2)
  })

  it('claves distintas no se mezclan', async () => {
    const a = compartirEnVuelo('a', () => Promise.resolve('A'))
    const b = compartirEnVuelo('b', () => Promise.resolve('B'))
    expect(await a).toBe('A')
    expect(await b).toBe('B')
  })

  it('un fallo tambien se olvida y no queda atascado', async () => {
    await expect(compartirEnVuelo('x', () => Promise.reject(new Error('fallo')))).rejects.toThrow('fallo')
    expect(await compartirEnVuelo('x', () => Promise.resolve('ok'))).toBe('ok')
  })

  it('olvidarEnVuelo hace que una lectura posterior no se sume a la anterior', async () => {
    let resolver: (v: string) => void = () => {}
    const lenta = compartirEnVuelo('x', () => new Promise<string>((r) => { resolver = r }))
    olvidarEnVuelo()
    const nueva = compartirEnVuelo('x', () => Promise.resolve('nueva'))
    expect(await nueva).toBe('nueva')
    resolver('vieja')
    expect(await lenta).toBe('vieja')
  })
})
