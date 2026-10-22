import { esperarTrabajo, esErrorTransitorio, MENSAJE_TIEMPO_AGOTADO, EstadoTrabajo } from '../esperarTrabajo'

const sinPausa = { dormir: async () => {} }

describe('esperarTrabajo', () => {
  it('devuelve el resultado cuando el trabajo termina', async () => {
    const respuestas: EstadoTrabajo<{ items: number }>[] = [
      { estado: 'procesando' },
      { estado: 'procesando' },
      { estado: 'listo', resultado: { items: 3 } },
    ]
    const consultar = jest.fn(async () => respuestas.shift()!)
    await expect(esperarTrabajo(consultar, sinPausa)).resolves.toEqual({ items: 3 })
    expect(consultar).toHaveBeenCalledTimes(3)
  })

  it('un error del trabajo se lanza con el mensaje del servidor', async () => {
    const consultar = async (): Promise<EstadoTrabajo<unknown>> => ({ estado: 'error', error: 'Error procesando ticket' })
    await expect(esperarTrabajo(consultar, sinPausa)).rejects.toThrow('Error procesando ticket')
  })

  it('tolera cortes de red puntuales y sigue consultando', async () => {
    let n = 0
    const consultar = async (): Promise<EstadoTrabajo<string>> => {
      n += 1
      if (n === 1) throw new TypeError('Failed to fetch')
      if (n === 2) throw new Error('Error HTTP 502')
      if (n === 3) return { estado: 'procesando' }
      return { estado: 'listo', resultado: 'ok' }
    }
    await expect(esperarTrabajo(consultar, sinPausa)).resolves.toBe('ok')
    expect(n).toBe(4)
  })

  it('los fallos de red se cuentan seguidos: un exito reinicia la cuenta', async () => {
    let n = 0
    const consultar = async (): Promise<EstadoTrabajo<string>> => {
      n += 1
      if (n === 20) return { estado: 'listo', resultado: 'ok' }
      if (n % 3 === 0) return { estado: 'procesando' }
      throw new TypeError('Failed to fetch')
    }
    await expect(esperarTrabajo(consultar, { ...sinPausa, maxFallosSeguidos: 2 })).resolves.toBe('ok')
  })

  it('se rinde tras demasiados fallos de red seguidos', async () => {
    const consultar = jest.fn(async (): Promise<EstadoTrabajo<string>> => { throw new TypeError('Failed to fetch') })
    await expect(esperarTrabajo(consultar, { ...sinPausa, maxFallosSeguidos: 3 })).rejects.toThrow('Failed to fetch')
    expect(consultar).toHaveBeenCalledTimes(4)
  })

  it('un error que no es de red (sesion caducada, no encontrado) no se reintenta', async () => {
    const consultar = jest.fn(async (): Promise<EstadoTrabajo<string>> => { throw new Error('No autenticado') })
    await expect(esperarTrabajo(consultar, sinPausa)).rejects.toThrow('No autenticado')
    expect(consultar).toHaveBeenCalledTimes(1)
  })

  it('agota el tiempo maximo con un mensaje claro', async () => {
    let reloj = 0
    const consultar = async (): Promise<EstadoTrabajo<string>> => ({ estado: 'procesando' })
    await expect(
      esperarTrabajo(consultar, { dormir: async (ms) => { reloj += ms }, ahora: () => reloj, maxMs: 10_000 }),
    ).rejects.toThrow(MENSAJE_TIEMPO_AGOTADO)
  })

  it('el intervalo crece sin pasar del maximo', async () => {
    const pausas: number[] = []
    let n = 0
    const consultar = async (): Promise<EstadoTrabajo<string>> => (++n < 12 ? { estado: 'procesando' } : { estado: 'listo', resultado: 'ok' })
    await esperarTrabajo(consultar, { dormir: async (ms) => { pausas.push(ms) }, intervaloMs: 1000, intervaloMaximoMs: 2500 })
    expect(pausas[0]).toBe(1000)
    expect(Math.max(...pausas)).toBe(2500)
    expect(pausas.every((p, i) => i === 0 || p >= pausas[i - 1])).toBe(true)
  })
})

describe('esErrorTransitorio', () => {
  it('reconoce cortes de red y 5xx', () => {
    expect(esErrorTransitorio(new TypeError('Failed to fetch'))).toBe(true)
    expect(esErrorTransitorio(new Error('Load failed'))).toBe(true)
    expect(esErrorTransitorio(new Error('Error HTTP 504'))).toBe(true)
    expect(esErrorTransitorio(new Error('Error HTTP 429'))).toBe(true)
  })

  it('no confunde errores definitivos', () => {
    expect(esErrorTransitorio(new Error('No autenticado'))).toBe(false)
    expect(esErrorTransitorio(new Error('Error HTTP 404'))).toBe(false)
    expect(esErrorTransitorio(null)).toBe(false)
  })
})
