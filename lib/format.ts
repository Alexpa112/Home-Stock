/** Formatea un importe monetario con el símbolo de moneda del hogar. */
export function formatImporte(valor: number, simbolo: string = '€'): string {
  return `${valor.toFixed(2)} ${simbolo}`
}
