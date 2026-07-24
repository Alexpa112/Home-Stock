'use client'

import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { listas as listasApi, permisos } from '@/lib/api'
import { getErrorMessage } from '@/lib/error-utils'
import { useActiveListSelection } from '@/hooks/useActiveListSelection'
import type { Lista, MiembroLista } from '@/lib/types'

interface ListasResponse {
  propias?: Lista[]
  compartidas?: Lista[]
}

interface MiembrosResponse {
  propietario: { nombre_usuario: string } | null
  miembros: MiembroLista[]
}

interface BusquedaUsuariosResponse {
  usuarios: { id: number; nombre_usuario: string; email: string | null }[]
}

export function useListsPage() {
  const [propias, setPropias] = useState<Lista[]>([])
  const [compartidas, setCompartidas] = useState<Lista[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [renombrandoId, setRenombrandoId] = useState<number | null>(null)
  const [nombreEditado, setNombreEditado] = useState('')
  const [compartiendoId, setCompartiendoId] = useState<number | null>(null)
  const [miembros, setMiembros] = useState<MiembroLista[]>([])
  const [propietario, setPropietario] = useState<{ nombre_usuario: string } | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [resultados, setResultados] = useState<{ id: number; nombre_usuario: string; email: string | null }[]>([])
  const [nivelNuevo, setNivelNuevo] = useState<'ver' | 'editar'>('editar')
  const { listaActivaId, persistListSelection } = useActiveListSelection()

  useEffect(() => {
    void cargar()
  }, [])

  const cargar = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await listasApi.listar() as ListasResponse
      setPropias(data.propias || [])
      setCompartidas(data.compartidas || [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const crearLista = async () => {
    if (!nuevoNombre.trim()) return

    try {
      setError('')
      const nueva = await listasApi.crear(nuevoNombre.trim()) as Lista
      setNuevoNombre('')
      await cargar()
      await seleccionarLista(nueva.id)
    } catch (err) {
      setError(getErrorMessage(err, 'Error al crear la lista'))
    }
  }

  const seleccionarLista = async (id: number) => {
    try {
      setError('')
      await listasApi.seleccionar(id)
      persistListSelection(id)
    } catch (err) {
      setError(getErrorMessage(err, 'Error al seleccionar la lista'))
    }
  }

  const iniciarRenombrar = (lista: Lista) => {
    setRenombrandoId(lista.id)
    setNombreEditado(lista.nombre)
  }

  const guardarRenombrar = async (id: number) => {
    if (!nombreEditado.trim()) {
      setRenombrandoId(null)
      return
    }

    try {
      setError('')
      await listasApi.actualizar(id, { nombre: nombreEditado.trim() })
      setRenombrandoId(null)
      await cargar()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al renombrar la lista'))
    }
  }

  const eliminarLista = async (id: number) => {
    try {
      setError('')
      await listasApi.eliminar(id)
      if (listaActivaId === id) persistListSelection(null)
      await cargar()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al eliminar la lista'))
    }
  }

  const salirLista = async (id: number) => {
    try {
      setError('')
      await listasApi.salir(id)
      if (listaActivaId === id) persistListSelection(null)
      await cargar()
    } catch (err) {
      setError(getErrorMessage(err, 'Error al salir de la lista'))
    }
  }

  const abrirCompartir = async (listaId: number) => {
    setCompartiendoId(listaId)
    setResultados([])
    setBusqueda('')

    try {
      const data = await permisos.miembros(listaId) as MiembrosResponse
      setPropietario(data.propietario)
      setMiembros(data.miembros || [])
    } catch (err) {
      setError(getErrorMessage(err, 'Error al cargar miembros'))
    }
  }

  const buscarUsuarios = async (query: string) => {
    setBusqueda(query)
    if (query.trim().length < 2) {
      setResultados([])
      return
    }

    try {
      const data = await permisos.buscarUsuarios(query.trim()) as BusquedaUsuariosResponse
      setResultados(data.usuarios || [])
    } catch {
      setResultados([])
    }
  }

  const compartirCon = async (nombreUsuario: string) => {
    if (!compartiendoId) return

    try {
      setError('')
      await permisos.compartir(compartiendoId, { usuario: nombreUsuario, nivel: nivelNuevo })
      await abrirCompartir(compartiendoId)
      setBusqueda('')
      setResultados([])
    } catch (err) {
      setError(getErrorMessage(err, 'Error al compartir'))
    }
  }

  const cambiarNivel = async (usuarioId: number, nivel: 'ver' | 'editar') => {
    if (!compartiendoId) return

    try {
      await permisos.actualizarPermiso(compartiendoId, usuarioId, nivel)
      await abrirCompartir(compartiendoId)
    } catch (err) {
      setError(getErrorMessage(err, 'Error al cambiar el permiso'))
    }
  }

  const quitarAcceso = async (usuarioId: number) => {
    if (!compartiendoId) return

    try {
      await permisos.revocar(compartiendoId, usuarioId)
      await abrirCompartir(compartiendoId)
    } catch (err) {
      setError(getErrorMessage(err, 'Error al quitar el acceso'))
    }
  }

  return {
    abrirCompartir,
    busqueda,
    buscarUsuarios,
    cambiarNivel,
    compartidas,
    compartiendoId,
    compartirCon,
    eliminarLista,
    error,
    guardarRenombrar,
    iniciarRenombrar,
    listaActivaId,
    loading,
    miembros,
    nivelNuevo,
    nombreEditado,
    nuevoNombre,
    propietario,
    propias,
    quitarAcceso,
    renombrandoId,
    resultados,
    salirLista,
    seleccionarLista,
    setCompartiendoId,
    setNivelNuevo,
    setNombreEditado,
    setNuevoNombre,
    submitCrearLista: async (event: FormEvent) => {
      event.preventDefault()
      await crearLista()
    },
  }
}
