'use client'

import { createContext, useContext, useState, useEffect, useRef, ReactNode, useCallback } from 'react'
import { hogares as hogaresApi } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'

// Cada cuanto se revisa si algun otro miembro cambio el icono/color del
// hogar activo (mismo intervalo que lib/usePollingRefresh.ts, para no
// introducir una cadencia de red distinta sin motivo).
const INTERVALO_REVISION_TEMA_MS = 60000

interface Hogar {
  id: number
  nombre: string
  descripcion: string | null
  icono: string
  color: string
  privada: boolean
  usuario_propietario_id: number
  mi_rol?: string
  actualizado_por_nombre?: string | null
}

interface HogarContextType {
  propios: Hogar[]
  compartidos: Hogar[]
  hogarActivoId: number | null
  loading: boolean
  seleccionar: (id: number) => Promise<void>
  crear: (nombre: string) => Promise<void>
  refrescar: () => Promise<void>
  actualizarHogar: (id: number, datos: Record<string, unknown>) => Promise<void>
  avisoTemaHogar: string | null
  cerrarAvisoTemaHogar: () => void
}

const HogarContext = createContext<HogarContextType | undefined>(undefined)

export function HogarProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const [propios, setPropios] = useState<Hogar[]>([])
  const [compartidos, setCompartidos] = useState<Hogar[]>([])
  const [hogarActivoId, setHogarActivoId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [avisoTemaHogar, setAvisoTemaHogar] = useState<string | null>(null)

  // Ultimo icono/color visto por hogar, para detectar si el hogar activo
  // cambio de estilo entre una carga y la siguiente. edicionLocalRef evita
  // avisar cuando el cambio lo acaba de hacer el propio usuario desde este
  // mismo cliente (actualizarHogar). primeraCargaRef evita avisar en el
  // montaje inicial, donde "cambio" respecto a "nada" no significa nada.
  const temaAnteriorRef = useRef<Record<number, { color: string; icono: string }>>({})
  const edicionLocalRef = useRef(false)
  const primeraCargaRef = useRef(true)

  const cargar = useCallback(async () => {
    try {
      setLoading(true)
      const data: any = await hogaresApi.listar()
      const todos: Hogar[] = [...(data.propias || []), ...(data.compartidas || [])]
      const hogarActivoIdNuevo = data.hogar_actual_id ?? null

      if (!primeraCargaRef.current && !edicionLocalRef.current) {
        const activoNuevo = todos.find((h) => h.id === hogarActivoIdNuevo)
        const anterior = hogarActivoIdNuevo != null ? temaAnteriorRef.current[hogarActivoIdNuevo] : undefined
        if (activoNuevo && anterior && (activoNuevo.color !== anterior.color || activoNuevo.icono !== anterior.icono)) {
          setAvisoTemaHogar(
            activoNuevo.actualizado_por_nombre
              ? t('aviso_tema_hogar_cambiado_con_nombre').replace('{nombre}', activoNuevo.actualizado_por_nombre)
              : t('aviso_tema_hogar_cambiado')
          )
        }
      }

      temaAnteriorRef.current = Object.fromEntries(todos.map((h) => [h.id, { color: h.color, icono: h.icono }]))
      primeraCargaRef.current = false

      setPropios(data.propias || [])
      setCompartidos(data.compartidas || [])
      setHogarActivoId(hogarActivoIdNuevo)
    } catch {
      // Sin conexion: se mantiene el estado anterior; ProtectedRoute ya
      // habra redirigido si de verdad no hay sesion.
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    cargar()
  }, [cargar])

  // Revision periodica en segundo plano: el color/icono del hogar activo
  // puede cambiarlo otro miembro sin que este cliente haga nada. Se salta el
  // ciclo si la pestaña no esta visible, igual que lib/usePollingRefresh.ts.
  useEffect(() => {
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        cargar()
      }
    }, INTERVALO_REVISION_TEMA_MS)
    return () => clearInterval(interval)
  }, [cargar])

  const seleccionar = async (id: number) => {
    await hogaresApi.seleccionar(id)
    setHogarActivoId(id)
  }

  const crear = async (nombre: string) => {
    const nuevo: any = await hogaresApi.crear(nombre)
    await cargar()
    setHogarActivoId(nuevo.id)
  }

  const actualizarHogar = async (id: number, datos: Record<string, unknown>) => {
    edicionLocalRef.current = true
    try {
      await hogaresApi.actualizar(id, datos)
      await cargar()
    } finally {
      edicionLocalRef.current = false
    }
  }

  const cerrarAvisoTemaHogar = () => setAvisoTemaHogar(null)

  return (
    <HogarContext.Provider
      value={{
        propios,
        compartidos,
        hogarActivoId,
        loading,
        seleccionar,
        crear,
        refrescar: cargar,
        actualizarHogar,
        avisoTemaHogar,
        cerrarAvisoTemaHogar,
      }}
    >
      {children}
    </HogarContext.Provider>
  )
}

export function useHogar() {
  const context = useContext(HogarContext)
  if (context === undefined) {
    throw new Error('useHogar must be used within HogarProvider')
  }
  return context
}
