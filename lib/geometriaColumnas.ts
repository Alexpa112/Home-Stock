/** Reparto horizontal de un grafico de columnas (viewBox de 100 de ancho).
 *
 * Con pocos datos (un solo dia de consumo, p. ej.) repartir los 100 entre las
 * columnas existentes pintaba un unico bloque del ancho completo. Se reserva
 * siempre sitio para `minimoColumnas` y el grupo se centra. */
export const MINIMO_COLUMNAS = 7

export interface GeometriaColumnas {
  /** Ancho de cada hueco de columna (la columna ocupa el 70 % central). */
  anchoCol: number
  /** Desplazamiento a la izquierda para centrar el grupo. */
  desplazamiento: number
}

export function geometriaColumnas(total: number, minimoColumnas = MINIMO_COLUMNAS): GeometriaColumnas {
  const huecos = Math.max(total, minimoColumnas, 1)
  const anchoCol = 100 / huecos
  return { anchoCol, desplazamiento: (100 - anchoCol * total) / 2 }
}
