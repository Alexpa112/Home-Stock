'use client'

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { hogares as hogaresApi } from '@/lib/api'

interface Hogar {
  id: number
  nombre: string
  descripcion: string | null
  icono: string
  color: string
  privada: boolean
  usuario_propietario_id: number
  mi_rol?: string
}

interface HogarContextType {
  propios: Hogar[]
  compartidos: Hogar[]
  hogarActivoId: number | null
  loading: boolean
  seleccionar: (id: number) => Promise<void>
  crear: (nombre: string) => Promise<void>
  refrescar: () => Promise<void>
}

const HogarContext = createContext<HogarContextType | undefined>(undefined)

export function HogarProvider({ children }: { children: ReactNode }) {
  const [propios, setPropios] = useState<Hogar[]>([])
  const [compartidos, setCompartidos] = useState<Hogar[]>([])
  const [hogarActivoId, setHogarActivoId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  const cargar = useCallback(async () => {
    try {
      setLoading(true)
      const data: any = await hogaresApi.listar()
      setPropios(data.propias || [])
      setCompartidos(data.compartidas || [])
      setHogarActivoId(data.hogar_actual_id ?? null)
    } catch {
      // Sin conexion: se mantiene el estado anterior; ProtectedRoute ya
      // habra redirigido si de verdad no hay sesion.
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    cargar()
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

  return (
    <HogarContext.Provider value={{ propios, compartidos, hogarActivoId, loading, seleccionar, crear, refrescar: cargar }}>
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
