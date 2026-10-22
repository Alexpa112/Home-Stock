/**
 * Espera a que termine un trabajo en segundo plano consultando su estado.
 *
 * El analisis de un ticket tarda entre segundos y minutos; hacerlo en una sola
 * peticion HTTP la cortaba cualquier intermediario (proxy de Next 30 s,
 * Cloudflare 100 s). Aqui el cliente consulta cada pocos segundos, asi que
 * ninguna peticion es larga y un corte de red puntual (movil que cambia de wifi
 * a datos, tunel que parpadea) se reintenta en vez de perder el analisis.
 */

export interface EstadoTrabajo<T> {
  estado: 'procesando' | 'listo' | 'error'
  resultado?: T
  error?: string
}

export interface OpcionesEspera {
  /** Pausa inicial entre consultas; crece hasta `intervaloMaximoMs`. */
  intervaloMs?: number
  intervaloMaximoMs?: number
  /** Tiempo total maximo esperando (por encima del tope del servidor). */
  maxMs?: number
  /** Fallos de red seguidos tolerados antes de rendirse. */
  maxFallosSeguidos?: number
  dormir?: (ms: number) => Promise<void>
  ahora?: () => number
}

export const MENSAJE_TIEMPO_AGOTADO =
  'La operación ha tardado demasiado. Prueba con una foto más ligera o con más luz.'

const dormirReal = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

/** Cortes de red o errores temporales del servidor/proxy: merece la pena reintentar. */
export function esErrorTransitorio(err: unknown): boolean {
  if (err instanceof TypeError) return true // fetch: "Failed to fetch", "Load failed", "NetworkError..."
  const mensaje = err instanceof Error ? err.message : String(err ?? '')
  return /failed to fetch|load failed|network|Error HTTP (5\d\d|429)/i.test(mensaje)
}

export async function esperarTrabajo<T>(
  consultar: () => Promise<EstadoTrabajo<T>>,
  opciones: OpcionesEspera = {},
): Promise<T> {
  const {
    intervaloMs = 1500,
    intervaloMaximoMs = 3000,
    maxMs = 6 * 60 * 1000,
    maxFallosSeguidos = 6,
    dormir = dormirReal,
    ahora = Date.now,
  } = opciones

  const inicio = ahora()
  let espera = intervaloMs
  let fallosSeguidos = 0

  while (ahora() - inicio < maxMs) {
    let estado: EstadoTrabajo<T> | null = null
    try {
      estado = await consultar()
      fallosSeguidos = 0
    } catch (err) {
      fallosSeguidos += 1
      if (!esErrorTransitorio(err) || fallosSeguidos > maxFallosSeguidos) throw err
    }

    if (estado) {
      if (estado.estado === 'listo') return estado.resultado as T
      if (estado.estado === 'error') throw new Error(estado.error || '')
    }

    await dormir(espera)
    espera = Math.min(Math.round(espera * 1.3), intervaloMaximoMs)
  }
  throw new Error(MENSAJE_TIEMPO_AGOTADO)
}
