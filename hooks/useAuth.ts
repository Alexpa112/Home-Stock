'use client'

import { useCallback, useEffect, useState } from 'react'
import { auth } from '@/lib/api'

interface User {
  usuario: string
  usuario_id: number
  nombre: string | null
  email: string | null
  tema_preferido: string
  idioma_preferido: string
}

interface AuthState {
  user: User | null
  loading: boolean
  error: string | null
  isAuthenticated: boolean
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
    isAuthenticated: false,
  })

  const checkAuth = useCallback(async () => {
    try {
      // /api/auth/estado es publica y siempre responde 200 (necesita serlo
      // para que la propia pagina de login sepa si hace falta el flujo de
      // "primer usuario"); la autenticacion real se lee del campo 'usuario'.
      const datos = await auth.estado()
      if (datos.usuario) {
        setState({
          user: {
            usuario: datos.usuario,
            usuario_id: datos.usuario_id,
            nombre: datos.nombre,
            email: datos.email,
            tema_preferido: datos.tema_preferido,
            idioma_preferido: datos.idioma_preferido,
          },
          loading: false,
          error: null,
          isAuthenticated: true,
        })
      } else {
        setState({ user: null, loading: false, error: null, isAuthenticated: false })
      }
    } catch (error) {
      console.error('Error comprobando sesion:', error)
      setState({
        user: null,
        loading: false,
        error: 'Error verificando autenticación',
        isAuthenticated: false,
      })
    }
  }, [])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return { ...state, refrescar: checkAuth }
}
