'use client'

import { useEffect, useState } from 'react'
import { Plus, Users, Check, Trash2, UserPlus, X, Pencil, LogOut, AlertCircle, Copy, Mail, MessageCircle } from 'lucide-react'
import { listas as listasApi, permisos } from '@/lib/api'
import { useHogar } from '@/contexts/HogarContext'

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
  const { seleccionar: seleccionarHogar, refrescar: refrescarHogar } = useHogar()
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
  const [confirmandoEliminarId, setConfirmandoEliminarId] = useState<number | null>(null)
  const [confirmandoSalirId, setConfirmandoSalirId] = useState<number | null>(null)
  const [confirmandoRevocarId, setConfirmandoRevocarId] = useState<number | null>(null)
  const [miembros, setMiembros] = useState<Miembro[]>([])
  const [propietario, setPropietario] = useState<{ nombre_usuario: string } | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [resultados, setResultados] = useState<{ id: number; nombre_usuario: string; email: string | null }[]>([])
  const [nivelNuevo, setNivelNuevo] = useState<'ver' | 'editar'>('editar')
  const [enlaceCompartible, setEnlaceCompartible] = useState<{ url: string; codigo: string; nombre_lista: string } | null>(null)
  const [cargandoEnlace, setCargandoEnlace] = useState(false)
  const [copiado, setCopiado] = useState(false)

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
      await seleccionarHogar(id)
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
    if (confirmandoEliminarId !== id) { setConfirmandoEliminarId(id); return }
    setConfirmandoEliminarId(null)
    try {
      setError('')
      await listasApi.eliminar(id)
      if (listaActivaId === id) {
        setListaActivaId(null)
        localStorage.removeItem(CLAVE_LISTA_ACTIVA)
      }
      await cargar()
      await refrescarHogar()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar la lista')
    }
  }

  const handleSalirLista = async (id: number) => {
    if (confirmandoSalirId !== id) { setConfirmandoSalirId(id); return }
    setConfirmandoSalirId(null)
    try {
      setError('')
      await listasApi.salir(id)
      if (listaActivaId === id) {
        setListaActivaId(null)
        localStorage.removeItem(CLAVE_LISTA_ACTIVA)
      }
      await cargar()
      await refrescarHogar()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al salir de la lista')
    }
  }

  const abrirCompartir = async (listaId: number) => {
    setCompartiendoId(listaId)
    setResultados([])
    setBusqueda('')
    setEnlaceCompartible(null)
    try {
      const data: any = await permisos.miembros(listaId)
      setPropietario(data.propietario)
      setMiembros(data.miembros || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar miembros')
    }
  }

  const generarEnlace = async (listaId: number) => {
    setCargandoEnlace(true)
    try {
      const data: any = await permisos.generarEnlace(listaId)
      setEnlaceCompartible(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al generar enlace')
    } finally {
      setCargandoEnlace(false)
    }
  }

  const copiarEnlace = async () => {
    if (!enlaceCompartible) return
    try {
      await navigator.clipboard.writeText(enlaceCompartible.url)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    } catch {
      setError('Error al copiar el enlace')
    }
  }

  const enviarPorMail = () => {
    if (!enlaceCompartible) return
    const asunto = `Te invito a la lista: ${enlaceCompartible.nombre_lista}`
    const cuerpo = `Hola! Quiero compartir mi lista "${enlaceCompartible.nombre_lista}" contigo.\n\nHaz clic aquí para aceptar:\n${enlaceCompartible.url}`
    window.open(`mailto:?subject=${encodeURIComponent(asunto)}&body=${encodeURIComponent(cuerpo)}`, '_blank')
  }

  const enviarPorWhatsApp = () => {
    if (!enlaceCompartible) return
    const mensaje = `Hola! Quiero compartir mi lista "${enlaceCompartible.nombre_lista}" contigo. 📱\n\n${enlaceCompartible.url}`
    const url = `https://wa.me/?text=${encodeURIComponent(mensaje)}`
    window.open(url, '_blank')
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
    if (confirmandoRevocarId !== usuarioId) { setConfirmandoRevocarId(usuarioId); return }
    setConfirmandoRevocarId(null)
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
                <button
                  onClick={() => iniciarRenombrar(lista)}
                  aria-label={`Renombrar lista ${lista.nombre}`}
                  className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-muted transition-colors"
                >
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
            <button onClick={() => abrirCompartir(lista.id)} className="btn-primary flex items-center gap-1.5 px-3">
              <Users className="w-4 h-4" /> Compartir
            </button>
            {confirmandoEliminarId === lista.id ? (
              <div className="flex gap-1">
                <button onClick={() => handleEliminarLista(lista.id)} className="px-3 h-11 text-xs font-semibold text-white bg-red-500 rounded-xl">Eliminar</button>
                <button onClick={() => setConfirmandoEliminarId(null)} className="px-3 h-11 text-xs font-semibold bg-muted rounded-xl">No</button>
              </div>
            ) : (
              <button
                onClick={() => handleEliminarLista(lista.id)}
                className="w-11 h-11 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors"
                aria-label="Eliminar lista"
              >
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            )}
          </>
        ) : (
          confirmandoSalirId === lista.id ? (
            <div className="flex gap-1">
              <button onClick={() => handleSalirLista(lista.id)} className="px-3 h-11 text-xs font-semibold text-white bg-red-500 rounded-xl">Salir</button>
              <button onClick={() => setConfirmandoSalirId(null)} className="px-3 h-11 text-xs font-semibold bg-muted rounded-xl">No</button>
            </div>
          ) : (
            <button
              onClick={() => handleSalirLista(lista.id)}
              className="btn-secondary flex items-center gap-1.5 text-red-600 dark:text-red-400"
            >
              <LogOut className="w-4 h-4" /> Salir
            </button>
          )
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
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Error</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleCrear} className="card flex gap-2">
        <label htmlFor="lista-nombre" className="sr-only">Nombre de la nueva lista</label>
        <input
          id="lista-nombre"
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
        <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-[9999] p-4">
          <div className="bg-card rounded-xl w-full max-w-md p-4 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Compartir lista</h2>
              <button onClick={() => setCompartiendoId(null)} className="p-1 hover:bg-muted rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Enlace compartible */}
            <div className="bg-muted/50 rounded-lg p-3 space-y-2">
              <h3 className="text-sm font-medium text-muted-foreground">Enlace compartible</h3>
              {enlaceCompartible ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 bg-background rounded px-2 py-1">
                    <input
                      type="text"
                      value={enlaceCompartible.url}
                      readOnly
                      className="flex-1 bg-transparent text-xs font-mono outline-none"
                    />
                    <button
                      onClick={copiarEnlace}
                      className="p-1 hover:bg-muted rounded transition-colors flex-shrink-0"
                      title="Copiar enlace"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={enviarPorMail}
                      className="btn-secondary flex-1 flex items-center justify-center gap-1 text-xs"
                    >
                      <Mail className="w-3.5 h-3.5" /> Email
                    </button>
                    <button
                      onClick={enviarPorWhatsApp}
                      className="btn-secondary flex-1 flex items-center justify-center gap-1 text-xs"
                    >
                      <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
                    </button>
                  </div>
                  {copiado && <p className="text-xs text-green-600 dark:text-green-400 text-center">✓ Enlace copiado</p>}
                </div>
              ) : (
                <button
                  onClick={() => generarEnlace(compartiendoId)}
                  disabled={cargandoEnlace}
                  className="btn-primary w-full text-sm disabled:opacity-50"
                >
                  {cargandoEnlace ? 'Generando...' : 'Generar enlace'}
                </button>
              )}
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
                      {confirmandoRevocarId === m.id ? (
                        <div className="flex gap-1">
                          <button onClick={() => quitarAcceso(m.id)} className="px-2 h-8 text-xs font-semibold text-white bg-red-500 rounded-lg">Quitar</button>
                          <button onClick={() => setConfirmandoRevocarId(null)} className="px-2 h-8 text-xs bg-muted rounded-lg">No</button>
                        </div>
                      ) : (
                        <button onClick={() => quitarAcceso(m.id)} className="w-9 h-9 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-lg" aria-label="Quitar acceso">
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </button>
                      )}
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
