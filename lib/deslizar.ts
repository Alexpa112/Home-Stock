// Lógica pura del gesto "deslizar a la derecha = comprado" de la lista de la
// compra. Vive aparte del componente para poder probarla sin navegador.

// Con 8 px de movimiento horizontal el toque deja de ser una pulsación: ahí se
// cancela la pulsación larga (editar) y empieza el deslizamiento.
export const UMBRAL_MOVIMIENTO = 8
// Desplazamiento a partir del cual, al soltar, se da por hecho el gesto.
export const UMBRAL_COMPLETA = 72
// Tope visual: la fila no sigue al dedo más allá de esto.
export const DESPLAZAMIENTO_MAXIMO = 112
// Los primeros píxeles del borde izquierdo son del gesto "atrás" del sistema.
export const MARGEN_BORDE = 24

export type Direccion = 'pendiente' | 'horizontal' | 'vertical'

export function clasificarMovimiento(dx: number, dy: number): Direccion {
  if (Math.abs(dx) < UMBRAL_MOVIMIENTO && Math.abs(dy) < UMBRAL_MOVIMIENTO) return 'pendiente'
  return Math.abs(dx) > Math.abs(dy) ? 'horizontal' : 'vertical'
}

// Solo hacia la derecha; hacia la izquierda la fila no se mueve.
export function desplazamientoVisible(dx: number): number {
  return Math.max(0, Math.min(dx, DESPLAZAMIENTO_MAXIMO))
}

export function gestoCompleto(dx: number): boolean {
  return dx >= UMBRAL_COMPLETA
}

export function empiezaEnElBorde(x: number): boolean {
  return x < MARGEN_BORDE
}
