// Lecturas identicas lanzadas a la vez (varios contextos y pantallas piden
// /api/auth/estado y /api/hogares al cargar) comparten UNA peticion mientras
// esta en curso. No es una cache: al resolver se olvida y la siguiente lectura
// vuelve a pedir datos.
const enVuelo = new Map<string, Promise<unknown>>()

export function compartirEnVuelo<T>(clave: string, peticion: () => Promise<T>): Promise<T> {
  const actual = enVuelo.get(clave) as Promise<T> | undefined
  if (actual) return actual
  const nueva = peticion().finally(() => {
    if (enVuelo.get(clave) === nueva) enVuelo.delete(clave)
  })
  enVuelo.set(clave, nueva)
  return nueva
}

export function olvidarEnVuelo(): void {
  enVuelo.clear()
}
