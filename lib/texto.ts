/**
 * Utilidades de texto para búsquedas que escribe el usuario.
 *
 * Vivía dentro de app/dashboard/historial/page.tsx, donde no se podía probar.
 * Aquí queda cubierta por lib/__tests__/texto.test.ts y disponible para
 * cualquier otro buscador de la app.
 */

/** Quita tildes y pasa a minúsculas para comparar sin depender de acentos. */
export function sinTildes(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

/**
 * Filtra una lista por coincidencia parcial en `nombre`, ignorando tildes,
 * mayúsculas y espacios sobrantes. Con la consulta vacía devuelve la lista tal
 * cual (no una copia): quien la use solo la lee.
 */
export function filtrarPorNombre<T extends { nombre: string }>(
  elementos: T[],
  consulta: string,
): T[] {
  const termino = sinTildes(consulta.trim())
  if (!termino) return elementos
  return elementos.filter((elemento) => sinTildes(elemento.nombre).includes(termino))
}
