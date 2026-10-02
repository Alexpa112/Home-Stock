// Reglas puras de la revisión de un ticket escaneado.

// Una cantidad con decimales y unidad "ud" casi nunca es real: lo normal es que
// sea un peso leído sin su unidad (caso real: "TOMATE PERA 0,850 kg" -> 0,85 ud).
// Se marca la línea para que el usuario la revise; no se bloquea la importación.
export function cantidadDudosa(cantidad: number | '', unidad: string): boolean {
  if (cantidad === '' || !Number.isFinite(cantidad)) return false
  return unidad.trim().toLowerCase() === 'ud' && !Number.isInteger(cantidad)
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
