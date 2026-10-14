// Reglas puras de la revisión de un ticket escaneado.

// Un peso o volumen mayor que esto en una compra domestica es casi siempre una
// coma perdida ("1,100 kg" leido como "100 kg"), no una compra real.
export const PESO_MAXIMO_PLAUSIBLE = 30

export type MotivoDuda = 'decimal_en_unidades' | 'peso_muy_alto'

// Por que una cantidad merece que el usuario la revise (o null si es creible):
//  - decimales con unidad "ud": casi nunca es real, lo normal es un peso leido
//    sin su unidad (caso real: "TOMATE PERA 0,850 kg" -> 0,85 ud).
//  - kg/l por encima de PESO_MAXIMO_PLAUSIBLE.
// Solo se marca la linea; no se bloquea la importacion.
export function motivoDeDuda(cantidad: number | '', unidad: string): MotivoDuda | null {
  if (cantidad === '' || !Number.isFinite(cantidad)) return null
  const u = unidad.trim().toLowerCase()
  if (u === 'ud' && !Number.isInteger(cantidad)) return 'decimal_en_unidades'
  if ((u === 'kg' || u === 'l') && cantidad > PESO_MAXIMO_PLAUSIBLE) return 'peso_muy_alto'
  return null
}

export function cantidadDudosa(cantidad: number | '', unidad: string): boolean {
  return motivoDeDuda(cantidad, unidad) !== null
}

// Número con el separador decimal del idioma del navegador (o el indicado).
export function formatearNumero(n: number, locale?: string): string {
  return n.toLocaleString(locale, { maximumFractionDigits: 3 })
}

// "×3" para unidades; "0,85 kg" para pesos y volúmenes.
export function textoCantidad(cantidad: number | '', unidad: string, locale?: string): string {
  if (cantidad === '') return ''
  const n = formatearNumero(cantidad, locale)
  return unidad.trim().toLowerCase() === 'ud' ? `×${n}` : `${n} ${unidad}`.trim()
}

// Mensajes que el navegador/proxy dan cuando NO hubo respuesta util del
// servidor: sin red, caida del tunel, 502/503/504/52x de Cloudflare. No son
// texto para el usuario ("Failed to fetch" no se traduce); la pantalla los
// sustituye por su propio mensaje.
export function esFalloDeRed(mensaje: string): boolean {
  return (
    /failed to fetch|load failed|networkerror|network request failed|fetch failed/i.test(mensaje) ||
    /^error http (502|503|504|52\d)\b/i.test(mensaje)
  )
}

// Precio por unidad (o por kg/l) de una linea, para el historial de precios.
// Si el ticket lo imprime ("1,89 EUR/kg", "4 x 0,55") se usa tal cual; si solo
// hay el importe de la linea, se divide por la cantidad ACTUAL (la que el
// usuario haya corregido). undefined si no hay dato fiable.
export function precioUnitarioDe(
  item: { precio_unitario?: number; precio_total?: number },
  cantidad: number | '',
): number | undefined {
  const unitario = Number(item.precio_unitario)
  if (Number.isFinite(unitario) && unitario > 0) return Math.round(unitario * 100) / 100
  const total = Number(item.precio_total)
  if (Number.isFinite(total) && total > 0 && cantidad !== '' && cantidad > 0) {
    return Math.round((total / cantidad) * 100) / 100
  }
  return undefined
}
