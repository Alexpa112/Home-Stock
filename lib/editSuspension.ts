// Registro global de "hay una edicion en curso": el Modal compartido
// (components/dashboard/Modal.tsx) marca aqui su apertura/cierre para que
// cualquier mecanismo de refresco automatico (useCacheBuster, polling) pueda
// aplazarse sin necesidad de que cada pantalla le pase su propio estado.
let contador = 0

export function suspenderPorEdicion(): void {
  contador++
}

export function reanudarPorEdicion(): void {
  contador = Math.max(0, contador - 1)
}

export function hayEdicionEnCurso(): boolean {
  return contador > 0
}
