'use client'

import { useEffect, useState } from 'react'
import { Plus, Users, Check, Trash2, UserPlus, X, Pencil, LogOut } from 'lucide-react'
import { listas as listasApi, permisos } from '@/lib/api'

interface Lista {
  id: number
  nombre: string
  descripcion: string | null
  icono: string
  color: string
  privada: boolean
  usuario_propietario_id: number
  mi_rol?: string
}

interface Miembro {
  id: number
  nombre_usuario: string
  email: string | null
  nivel: string
  fecha_otorgado?: string
}

const CLAVE_LISTA_ACTIVA = 'stockhogar-lista-activa-ui'

export default function ListasPage() {
  const [propias, setPropias] = useState<Lista[]>([])
  const [compartidas, setCompartidas] = useState<Lista[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [listaActivaId, setListaActivaId] = useState<number | null>(null)
  const [renombrandoId, setRenombrandoId] = useState<number | null>(null)
  const [nombreEditado, setNombreEditado] = useState('')

  // Panel de compartir (solo una lista abierta a la vez)
  const [compartiendoId, setCompartiendoId] = useState<number | null>(null)
  const [miembros, setMiembros] = useState<Miembro[]>([])
  const [propietario, setPropietario] = useState<{ nombre_usuario: string } | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [resultados, setResultados] = useState<{ id: number; nombre_usuario: string; email: string | null }[]>([])
  const [nivelNuevo, setNivelNuevo] = useState<'ver' | 'editar'>('editar')

  useEffect(() => {
    cargar()
    const guardada = localStorage.getItem(CLAVE_LISTA_ACTIVA)
    if (guardada) setListaActivaId(parseInt(guardada, 10))
  }, [])

  const cargar = async () => {
    try {
      setLoading(true)
      setError('')
      const data: any = await listasApi.listar()
      setPropias(data.propias || [])
      setCompartidas(data.compartidas || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de conexión')
    } finally {
      setLoading(false)
    }
  }

  const handleCrear = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nuevoNombre.trim()) return
    try {
      setError('')
      const nueva: any = await listasApi.crear(nuevoNombre.trim())
      setNuevoNombre('')
      await cargar()
      handleSeleccionar(nueva.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear la lista')
    }
  }

  const handleSeleccionar = async (id: number) => {
    try {
      setError('')
      await listasApi.seleccionar(id)
      setListaActivaId(id)
      localStorage.setItem(CLAVE_LISTA_ACTIVA, String(id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al seleccionar la lista')
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
      setError(err instanceof Error ? err.message : 'Error al renombrar la lista')
    }
  }

  const handleEliminarLista = async (id: number) => {
    if (!confirm('¿Eliminar esta lista y todos sus artículos? Esta acción no se puede deshacer.')) return
    try {
      setError('')
      await listasApi.eliminar(id)
      if (listaActivaId === id) {
        setListaActivaId(null)
        localStorage.removeItem(CLAVE_LISTA_ACTIVA)
      }
      await cargar()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar la lista')
    }
  }

  const handleSalirLista = async (id: number) => {
    if (!confirm('¿Salir de esta lista compartida? Dejarás de tener acceso a ella.')) return
    try {
      setError('')
      await listasApi.salir(id)
      if (listaActivaId === id) {
        setListaActivaId(null)
        localStorage.removeItem(CLAVE_LISTA_ACTIVA)
      }
      await cargar()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al salir de la lista')
    }
  }

  const abrirCompartir = async (listaId: number) => {
    setCompartiendoId(listaId)
    setResultados([])
    setBusqueda('')
    try {
      const data: any = await permisos.miembros(listaId)
      setPropietario(data.propietario)
      setMiembros(data.miembros || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar miembros')
    }
  }

  const buscarUsuarios = async (q: string) => {
    setBusqueda(q)
    if (q.trim().length < 2) {
      setResultados([])
      return
    }
    try {
      const data: any = await permisos.buscarUsuarios(q.trim())
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
      setError(err instanceof Error ? err.message : 'Error al compartir')
    }
  }

  const cambiarNivel = async (usuarioId: number, nivel: 'ver' | 'editar') => {
    if (!compartiendoId) return
    try {
      await permisos.actualizarPermiso(compartiendoId, usuarioId, nivel)
      await abrirCompartir(compartiendoId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cambiar el permiso')
    }
  }

  const quitarAcceso = async (usuarioId: number) => {
    if (!compartiendoId) return
    if (!confirm('¿Quitar el acceso de este usuario a la lista?')) return
    try {
      await permisos.revocar(compartiendoId, usuarioId)
      await abrirCompartir(compartiendoId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al quitar el acceso')
    }
  }

  const renderLista = (lista: Lista, esPropia: boolean) => (
    <div key={lista.id} className="card space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          {renombrandoId === lista.id ? (
            <div className="flex gap-2">
              <input
                type="text"
                value={nombreEditado}
                onChange={(e) => setNombreEditado(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && guardarRenombrar(lista.id)}
                className="input-field !py-1"
                autoFocus
              />
              <button onClick={() => guardarRenombrar(lista.id)} className="btn-secondary !py-1">
                <Check className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <h3 className="font-semibold flex items-center gap-2">
              {lista.nombre}
              {esPropia && (
                <button onClick={() => iniciarRenombrar(lista)} aria-label="Renombrar">
                  <Pencil className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
              )}
            </h3>
          )}
          {lista.descripcion && <p className="text-sm text-muted-foreground">{lista.descripcion}</p>}
          <p className="text-xs text-muted-foreground mt-1">
            {esPropia ? 'Propietario' : `Compartida (${lista.mi_rol === 'editar' ? 'puedes editar' : 'solo ver'})`}
          </p>
        </div>
        {listaActivaId === lista.id && (
          <span className="flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400 flex-shrink-0">
            <Check className="w-4 h-4" /> Activa
          </span>
        )}
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => handleSeleccionar(lista.id)}
          disabled={listaActivaId === lista.id}
          className="btn-secondary flex-1 disabled:opacity-50"
        >
          {listaActivaId === lista.id ? 'Ya activa' : 'Usar esta lista'}
        </button>
        {esPropia ? (
          <>
            <button onClick={() => abrirCompartir(lista.id)} className="btn-primary flex items-center gap-1">
              <Users className="w-4 h-4" /> Compartir
            </button>
            <button
              onClick={() => handleEliminarLista(lista.id)}
              className="p-2 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg"
              aria-label="Eliminar lista"
            >
              <Trash2 className="w-4 h-4 text-red-500" />
            </button>
          </>
        ) : (
          <button
            onClick={() => handleSalirLista(lista.id)}
            className="btn-secondary flex items-center gap-1 text-red-600 dark:text-red-400"
          >
            <LogOut className="w-4 h-4" /> Salir
          </button>
        )}
      </div>
    </div>
  )

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">Mis Listas</h1>
        <p className="text-muted-foreground mt-1">
          La lista "activa" es la que ves en Stock y en la Lista de la Compra
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg text-sm">{error}</div>
      )}

      <form onSubmit={handleCrear} className="card flex gap-2">
        <input
          type="text"
          value={nuevoNombre}
          onChange={(e) => setNuevoNombre(e.target.value)}
          placeholder="Nombre de la nueva lista"
          className="input-field flex-1"
        />
        <button type="submit" className="btn-primary flex items-center gap-1">
          <Plus className="w-4 h-4" /> Crear
        </button>
      </form>

      {loading ? (
        <p className="text-center text-muted-foreground py-8">Cargando listas...</p>
      ) : (
        <>
          {propias.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">Propias</h2>
              <div className="grid gap-3">{propias.map((l) => renderLista(l, true))}</div>
            </div>
          )}
          {compartidas.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">Compartidas conmigo</h2>
              <div className="grid gap-3">{compartidas.map((l) => renderLista(l, false))}</div>
            </div>
          )}
          {propias.length === 0 && compartidas.length === 0 && (
            <p className="text-center text-muted-foreground py-8">Aún no tienes ninguna lista. Crea la primera arriba.</p>
          )}
        </>
      )}

      {/* Panel de compartir */}
      {compartiendoId !== null && (
        <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-4">
          <div className="bg-card rounded-xl w-full max-w-md p-4 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Compartir lista</h2>
              <button onClick={() => setCompartiendoId(null)} className="p-1 hover:bg-muted rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <h3 className="text-sm font-medium text-muted-foreground mb-2">Con acceso</h3>
              <div className="space-y-2">
                {propietario && (
                  <div className="flex items-center justify-between text-sm">
                    <span>{propietario.nombre_usuario} (tú)</span>
                    <span className="text-muted-foreground">Propietario</span>
                  </div>
                )}
                {miembros.map((m) => (
                  <div key={m.id} className="flex items-center justify-between text-sm gap-2">
                    <span className="truncate">{m.nombre_usuario}</span>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <select
                        value={m.nivel}
                        onChange={(e) => cambiarNivel(m.id, e.target.value as 'ver' | 'editar')}
                        className="input-field !py-1 !px-2 text-xs"
                      >
                        <option value="ver">Solo ver</option>
                        <option value="editar">Puede editar</option>
                      </select>
                      <button onClick={() => quitarAcceso(m.id)} aria-label="Quitar acceso">
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </div>
                  </div>
                ))}
                {miembros.length === 0 && (
                  <p className="text-xs text-muted-foreground">Nadie más tiene acceso todavía.</p>
                )}
              </div>
            </div>

            <div className="border-t border-border pt-4 space-y-2">
              <h3 className="text-sm font-medium text-muted-foreground">Añadir usuario</h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={busqueda}
                  onChange={(e) => buscarUsuarios(e.target.value)}
                  placeholder="Nombre de usuario o email (min. 2 letras)"
                  className="input-field flex-1"
                />
                <select
                  value={nivelNuevo}
                  onChange={(e) => setNivelNuevo(e.target.value as 'ver' | 'editar')}
                  className="input-field w-32"
                >
                  <option value="editar">Editar</option>
                  <option value="ver">Ver</option>
                </select>
              </div>
              {resultados.length > 0 && (
                <div className="space-y-1">
                  {resultados.map((u) => (
                    <button
                      key={u.id}
                      onClick={() => compartirCon(u.nombre_usuario)}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-muted text-sm"
                    >
                      <span>{u.nombre_usuario}</span>
                      <UserPlus className="w-4 h-4 text-accent" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
