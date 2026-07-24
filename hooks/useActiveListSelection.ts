'use client'

import { useCallback, useEffect, useState } from 'react'

export const ACTIVE_LIST_STORAGE_KEY = 'stockhogar-lista-activa-ui'

export function useActiveListSelection() {
  const [listaActivaId, setListaActivaId] = useState<number | null>(null)

  useEffect(() => {
    const saved = window.localStorage.getItem(ACTIVE_LIST_STORAGE_KEY)
    if (!saved) return

    const parsed = parseInt(saved, 10)
    setListaActivaId(Number.isNaN(parsed) ? null : parsed)
  }, [])

  const persistListSelection = useCallback((listaId: number | null) => {
    setListaActivaId(listaId)

    if (listaId === null) {
      window.localStorage.removeItem(ACTIVE_LIST_STORAGE_KEY)
      return
    }

    window.localStorage.setItem(ACTIVE_LIST_STORAGE_KEY, String(listaId))
  }, [])

  return {
    listaActivaId,
    persistListSelection,
  }
}
