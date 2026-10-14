// Epígrafe que hay que pintar ANTES de la acción `i` de un menú: solo en la
// primera acción de cada grupo consecutivo (y nunca si la acción no tiene grupo).
export function epigrafeAntesDe<T extends { grupo?: string }>(
  acciones: T[],
  i: number,
): string | undefined {
  const grupo = acciones[i]?.grupo
  if (!grupo) return undefined
  return i === 0 || acciones[i - 1].grupo !== grupo ? grupo : undefined
}
