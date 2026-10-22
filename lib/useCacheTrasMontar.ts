import { useEffect, useLayoutEffect } from 'react'

// useLayoutEffect avisa al renderizar en el servidor; ahi basta useEffect (que
// tampoco se ejecuta). En el navegador corre antes del primer pintado.
const useEfectoIsomorfico = typeof window === 'undefined' ? useEffect : useLayoutEffect

/**
 * Carga datos de lib/dataCache DESPUES de montar, no al inicializar el estado.
 *
 * `useState(() => getCached(...))` lee localStorage durante el primer render del
 * cliente, pero el servidor no lo tiene: el HTML del servidor sale con la lista
 * vacia, el cliente hidrata con datos y React lanza el error #418 (y descarta
 * el HTML del servidor). Con este hook el primer render del cliente coincide
 * con el del servidor, y al ejecutarse antes del primer pintado el usuario ve
 * igualmente el ultimo dato conocido sin parpadeo.
 */
export function useCacheTrasMontar(cargar: () => void): void {
  useEfectoIsomorfico(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
