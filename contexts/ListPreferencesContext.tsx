'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { auth } from '@/lib/api'

interface ListPreferences {
  vista_lista_compra: 'lista' | 'recuadros'
  agrupar_categorias: 'on' | 'off'
}

interface ListPreferencesContextType {
  preferences: ListPreferences
  loading: boolean
  updatePreferences: (prefs: Partial<ListPreferences>) => Promise<void>
}

const ListPreferencesContext = createContext<ListPreferencesContextType | undefined>(undefined)

export function ListPreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<ListPreferences>({
    vista_lista_compra: 'lista',
    agrupar_categorias: 'off',
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadPreferences()
  }, [])

  const loadPreferences = async () => {
    try {
      const data: any = await auth.estado()
      setPreferences({
        vista_lista_compra: data.vista_lista_compra || 'lista',
        agrupar_categorias: data.agrupar_categorias || 'off',
      })
    } catch (err) {
      console.error('Error loading preferences:', err)
    } finally {
      setLoading(false)
    }
  }

  const updatePreferences = async (prefs: Partial<ListPreferences>) => {
    try {
      const newPrefs = { ...preferences, ...prefs }
      const result: any = await auth.actualizarPreferenciasListas({
        vista_lista_compra: newPrefs.vista_lista_compra,
        agrupar_categorias: newPrefs.agrupar_categorias,
      })
      setPreferences({
        vista_lista_compra: result.vista_lista_compra || 'lista',
        agrupar_categorias: result.agrupar_categorias || 'off',
      })
    } catch (err) {
      console.error('Error updating preferences:', err)
      throw err
    }
  }

  return (
    <ListPreferencesContext.Provider value={{ preferences, loading, updatePreferences }}>
      {children}
    </ListPreferencesContext.Provider>
  )
}

export function useListPreferences() {
  const context = useContext(ListPreferencesContext)
  if (context === undefined) {
    throw new Error('useListPreferences must be used within ListPreferencesProvider')
  }
  return context
}
