'use client'

import { useState } from 'react'
import { Home, Plus, Users, X, Check, Copy, Mail, MessageCircle, UserPlus, Trash2 } from 'lucide-react'
import { useHogar } from '@/contexts/HogarContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { hogares as hogaresApi, permisos } from '@/lib/api'
import { clearCache } from '@/lib/dataCache'
import { IconPicker, ICONOS_HOGAR } from '@/components/dashboard/IconPicker'
import { IconRenderer } from '@/components/dashboard/IconRenderer'

// Claves de lib/dataCache.ts que dependen del hogar activo: hay que limpiarlas
// antes de recargar para no pintar un instante los datos del hogar anterior
// (esas claves no van separadas por hogar, ver el comentario de clearCache).
const CACHE_KEYS_POR_HOGAR = ['stock:productos', 'stock:categorias', 'shopping:articulos']

interface Props {
  // Si se pasa, aparece una X para cerrar sin cambiar de hogar (uso: cambiar
  // de hogar desde dentro de la app). Si no se pasa, es la pantalla
  // obligatoria de entrada (sin hogar activo todavia) y no hay forma de
  // cerrarla sin elegir uno.
  onCerrar?: () => void
}

export function SelectorHogarPantallaCompleta({ onCerrar }: Props) {
  const { propios, compartidos, seleccionar, crear, refrescar, actualizarHogar } = useHogar()
  const { t } = useTranslation()
  const [entrandoId, setEntrandoId] = useState<number | null>(null)
  const [creando, setCreando] = useState(false)
  const [nombreNuevo, setNombreNuevo] = useState('')
  const [error, setError] = useState('')
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [nombreEditado, setNombreEditado] = useState('')
  const [colorEditado, setColorEditado] = useState('')
  const [iconoEditado, setIconoEditado] = useState<string | null>(null)
  const [eligiendoIcono, setEligiendoIcono] = useState(false)
  const [confirmandoEliminarId, setConfirmandoEliminarId] = useState<number | null>(null)
  const [confirmandoSalirId, setConfirmandoSalirId] = useState<number | null>(null)
  const [coloresDisponibles] = useState(['#B5551A', '#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6', '#1ABC9C', '#34495E'])

  // Panel de compartir (solo un hogar abierto a la vez)
  const [compartiendoId, setCompartiendoId] = useState<number | null>(null)
  const [confirmandoRevocarId, setConfirmandoRevocarId] = useState<number | null>(null)
  const [miembros, setMiembros] = useState<{ id: number; nombre_usuario: string; email: string | null; nivel: string }[]>([])
  const [propietario, setPropietario] = useState<{ nombre_usuario: string } | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [resultados, setResultados] = useState<{ id: number; nombre_usuario: string; email: string | null }[]>([])
  const [nivelNuevo, setNivelNuevo] = useState<'ver' | 'comprar' | 'editar'>('editar')
  const [enlaceCompartible, setEnlaceCompartible] = useState<{ url: string; codigo: string; nombre_lista: string } | null>(null)
  const [cargandoEnlace, setCargandoEnlace] = useState(false)
  const [copiado, setCopiado] = useState(false)

  const hogares = [...propios, ...compartidos]

  // Reentrada "de verdad": el estado de Stock/Compra viene de cache local
  // (lib/dataCache.ts) sin separar por hogar, asi que un cambio "en caliente"
  // podria enseñar por un instante datos del hogar anterior. Recargamos la
  // app entera en vez de solo actualizar el estado en memoria.
  const handleEntrar = async (id: number) => {
    setEntrandoId(id)
    setError('')
    try {
      await seleccionar(id)
      clearCache(CACHE_KEYS_POR_HOGAR)
      window.location.href = '/dashboard'
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_entrar_hogar'))
      setEntrandoId(null)
    }
  }

  const handleCrear = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nombreNuevo.trim()) return
    setError('')
    try {
      await crear(nombreNuevo.trim())
      clearCache(CACHE_KEYS_POR_HOGAR)
      window.location.href = '/dashboard'
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_crear_hogar'))
    }
  }

  const iniciarEdicion = (hogar: { id: number; nombre: string; color?: string; icono?: string }) => {
    setEditandoId(hogar.id)
    setNombreEditado(hogar.nombre)
    setColorEditado(hogar.color || '#B5551A')
    setIconoEditado(hogar.icono || null)
  }

  const guardarEdicion = async (id: number) => {
    if (!nombreEditado.trim()) {
      setEditandoId(null)
      return
    }
    try {
      await actualizarHogar(id, { nombre: nombreEditado.trim(), color: colorEditado, icono: iconoEditado })
      setEditandoId(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_renombrar_hogar'))
    }
  }

  const handleEliminar = async (id: number) => {
    if (confirmandoEliminarId !== id) {
      setConfirmandoEliminarId(id)
      return
    }
    setConfirmandoEliminarId(null)
    try {
      await hogaresApi.eliminar(id)
      await refrescar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_hogar'))
    }
  }

  const handleSalir = async (id: number) => {
    if (confirmandoSalirId !== id) {
      setConfirmandoSalirId(id)
      return
    }
    setConfirmandoSalirId(null)
    try {
      await hogaresApi.salir(id)
      await refrescar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_error_al_salir_hogar'))
    }
  }

  const abrirCompartir = async (hogarId: number) => {
    setCompartiendoId(hogarId)
    setResultados([])
    setBusqueda('')
    setEnlaceCompartible(null)
    try {
      const data: any = await permisos.miembros(hogarId)
      setPropietario(data.propietario)
      setMiembros(data.miembros || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_error_al_cargar_miembros'))
    }
  }

  const generarEnlace = async (hogarId: number) => {
    setCargandoEnlace(true)
    try {
      const data: any = await permisos.generarEnlace(hogarId)
      setEnlaceCompartible(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_generar_enlace'))
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
      setError(t('err_copiar_enlace'))
    }
  }

  const enviarPorMail = () => {
    if (!enlaceCompartible) return
    const asunto = t('email_asunto_invitacion_hogar').replace('{nombre}', enlaceCompartible.nombre_lista)
    const cuerpo = t('email_cuerpo_invitacion_hogar').replace('{nombre}', enlaceCompartible.nombre_lista).replace('{enlace}', enlaceCompartible.url)
    window.open(`mailto:?subject=${encodeURIComponent(asunto)}&body=${encodeURIComponent(cuerpo)}`, '_blank')
  }

  const enviarPorWhatsApp = () => {
    if (!enlaceCompartible) return
    const mensaje = t('whatsapp_mensaje_compartir_hogar').replace('{nombre}', enlaceCompartible.nombre_lista).replace('{enlace}', enlaceCompartible.url)
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
      setError(err instanceof Error ? err.message : t('err_compartir'))
    }
  }

  const cambiarNivel = async (usuarioId: number, nivel: 'ver' | 'comprar' | 'editar') => {
    if (!compartiendoId) return
    try {
      await permisos.actualizarPermiso(compartiendoId, usuarioId, nivel)
      await abrirCompartir(compartiendoId)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_error_al_actualizar_permiso'))
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
      setError(err instanceof Error ? err.message : t('err_error_al_revocar_acceso'))
    }
  }

  return (
    <div className="fixed inset-0 z-[9999] bg-background overflow-y-auto">
      <div className="w-full max-w-md mx-auto p-4 pt-6 pb-10 space-y-5">
        <div className="flex items-center justify-between">
          <div className="w-8" />
          <h1 className="text-lg font-bold">{t('tus_hogares')}</h1>
          {onCerrar ? (
            <button
              onClick={onCerrar}
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-muted"
              aria-label={t('cancelar')}
            >
              <X className="w-5 h-5" />
            </button>
          ) : (
            <div className="w-8" />
          )}
        </div>

        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 text-sm rounded-lg">{error}</div>
        )}

        <div className="space-y-3">
          {hogares.map((hogar) => {
            const esPropia = propios.some((p) => p.id === hogar.id)
            const editando = editandoId === hogar.id
            return (
              <div key={hogar.id}>
                <button
                  onClick={() => handleEntrar(hogar.id)}
                  disabled={entrandoId !== null}
                  className="w-full card !p-3 flex items-center gap-3 text-left disabled:opacity-60 hover:bg-muted/50 transition-colors"
                >
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-white" style={{ backgroundColor: hogar.color || '#B5551A' }}>
                    {hogar.icono ? <IconRenderer name={hogar.icono} className="w-5 h-5" /> : <Home className="w-5 h-5" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm truncate">{hogar.nombre}</p>
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      {esPropia ? (
                        t('propietario_rol')
                      ) : (
                        <>
                          <Users className="w-3 h-3" /> {
                            hogar.mi_rol === 'editar'
                              ? t('compartida_puedes_editar')
                              : hogar.mi_rol === 'comprar'
                                ? t('compartida_puede_comprar')
                                : t('compartida_solo_ver')
                          }
                        </>
                      )}
                    </p>
                  </div>
                  {entrandoId === hogar.id && <span className="text-xs text-muted-foreground shrink-0">{t('entrando')}</span>}
                </button>

                {entrandoId === null && esPropia && (
                  <div className="flex mt-1">
                    <button
                      onClick={() => editando ? setEditandoId(null) : iniciarEdicion(hogar)}
                      className="flex-1 px-3 py-2 text-sm text-muted-foreground hover:text-accent hover:bg-muted rounded-lg transition-colors"
                    >
                      {editando ? t('cancelar') : t('editar')}
                    </button>
                    <button
                      onClick={() => compartiendoId === hogar.id ? setCompartiendoId(null) : abrirCompartir(hogar.id)}
                      className="flex-1 px-3 py-2 text-sm text-muted-foreground hover:text-accent hover:bg-muted rounded-lg transition-colors flex items-center justify-center gap-1.5"
                    >
                      <Users className="w-3.5 h-3.5" /> {t('compartir')}
                    </button>
                  </div>
                )}

                {editando && esPropia && (
                  <div className="card !p-4 mt-2 space-y-4 bg-muted/30">
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground block mb-2">{t('nombre')}</label>
                      <input
                        type="text"
                        value={nombreEditado}
                        onChange={(e) => setNombreEditado(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && guardarEdicion(hogar.id)}
                        className="input-field"
                        autoFocus
                      />
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-muted-foreground block mb-2">{t('color')}</label>
                      <div className="grid grid-cols-4 gap-2">
                        {coloresDisponibles.map((color) => (
                          <button
                            key={color}
                            onClick={() => setColorEditado(color)}
                            className={`w-full aspect-square rounded-lg border-2 transition-all ${
                              colorEditado === color ? 'border-accent shadow-md' : 'border-border'
                            }`}
                            style={{ backgroundColor: color }}
                            title={color}
                          />
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-muted-foreground block mb-2">{t('icono')}</label>
                      <button
                        type="button"
                        onClick={() => setEligiendoIcono(true)}
                        className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-muted transition-colors"
                      >
                        <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 text-white" style={{ backgroundColor: colorEditado }}>
                          {iconoEditado ? <IconRenderer name={iconoEditado} className="w-5 h-5" /> : <Home className="w-5 h-5" />}
                        </div>
                        <span className="text-sm text-muted-foreground">{t('elegir_icono')}</span>
                      </button>
                    </div>

                    <div className="border-t border-border pt-4 space-y-2">
                      <button
                        onClick={() => guardarEdicion(hogar.id)}
                        disabled={!nombreEditado.trim()}
                        className="w-full px-3 py-2.5 bg-accent text-white rounded-lg font-medium text-sm hover:bg-accent/90 transition-colors disabled:opacity-50"
                      >
                        {t('guardar')}
                      </button>
                      <button
                        onClick={() => setEditandoId(null)}
                        className="w-full px-3 py-2.5 bg-muted rounded-lg font-medium text-sm hover:bg-muted/80 transition-colors"
                      >
                        {t('cancelar')}
                      </button>
                    </div>

                    <div className="border-t border-border pt-4 space-y-2">
                      {confirmandoEliminarId === hogar.id ? (
                        <>
                          <p className="text-xs text-center text-muted-foreground mb-2">{t('confirmar_eliminar_hogar')}</p>
                          <button
                            onClick={() => handleEliminar(hogar.id)}
                            className="w-full px-3 py-2.5 bg-red-600 text-white rounded-lg font-medium text-sm hover:bg-red-700 transition-colors"
                          >
                            {t('si')}
                          </button>
                          <button
                            onClick={() => setConfirmandoEliminarId(null)}
                            className="w-full px-3 py-2.5 bg-muted rounded-lg font-medium text-sm hover:bg-muted/80 transition-colors"
                          >
                            {t('no')}
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleEliminar(hogar.id)}
                          className="w-full px-3 py-2.5 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 rounded-lg font-medium text-sm hover:bg-red-100 dark:hover:bg-red-950/50 transition-colors"
                        >
                          {t('eliminar')}
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {compartiendoId === hogar.id && esPropia && (
                  <div className="card !p-4 mt-2 space-y-4 bg-muted/30">
                    <div className="bg-background/60 rounded-lg p-3 space-y-2">
                      <h3 className="text-sm font-medium text-muted-foreground">{t('enlace_compartible_titulo')}</h3>
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
                              title={t('copiar_enlace')}
                            >
                              <Copy className="w-4 h-4" />
                            </button>
                          </div>
                          <div className="flex gap-1">
                            <button
                              onClick={enviarPorMail}
                              className="btn-secondary flex-1 flex items-center justify-center gap-1 text-xs"
                            >
                              <Mail className="w-3.5 h-3.5" /> {t('email')}
                            </button>
                            <button
                              onClick={enviarPorWhatsApp}
                              className="btn-secondary flex-1 flex items-center justify-center gap-1 text-xs"
                            >
                              <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
                            </button>
                          </div>
                          {copiado && <p className="text-xs text-green-600 dark:text-green-400 text-center">✓ {t('enlace_copiado_portapapeles')}</p>}
                        </div>
                      ) : (
                        <button
                          onClick={() => generarEnlace(hogar.id)}
                          disabled={cargandoEnlace}
                          className="btn-primary w-full text-sm disabled:opacity-50"
                        >
                          {cargandoEnlace ? t('generando') : t('generar_enlace_compartible')}
                        </button>
                      )}
                    </div>

                    <div>
                      <h3 className="text-sm font-medium text-muted-foreground mb-2">{t('con_acceso')}</h3>
                      <div className="space-y-2">
                        {propietario && (
                          <div className="flex items-center justify-between text-sm">
                            <span>{propietario.nombre_usuario} {t('tu_suffix')}</span>
                            <span className="text-muted-foreground">{t('propietario_rol')}</span>
                          </div>
                        )}
                        {miembros.map((m) => (
                          <div key={m.id} className="flex items-center justify-between text-sm gap-2">
                            <span className="truncate">{m.nombre_usuario}</span>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <select
                                value={m.nivel}
                                onChange={(e) => cambiarNivel(m.id, e.target.value as 'ver' | 'comprar' | 'editar')}
                                className="input-field !py-1 !px-2 text-xs"
                              >
                                <option value="ver">{t('permiso_ver')}</option>
                                <option value="comprar">{t('puede_comprar')}</option>
                                <option value="editar">{t('puede_editar')}</option>
                              </select>
                              {confirmandoRevocarId === m.id ? (
                                <div className="flex gap-1">
                                  <button onClick={() => quitarAcceso(m.id)} className="px-2 h-8 text-xs font-semibold text-white bg-red-500 rounded-lg">{t('quitar')}</button>
                                  <button onClick={() => setConfirmandoRevocarId(null)} className="px-2 h-8 text-xs bg-muted rounded-lg">{t('no')}</button>
                                </div>
                              ) : (
                                <button onClick={() => quitarAcceso(m.id)} className="w-9 h-9 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-lg" aria-label={t('aria_quitar_acceso')}>
                                  <Trash2 className="w-4 h-4 text-red-500" />
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                        {miembros.length === 0 && (
                          <p className="text-xs text-muted-foreground">{t('nadie_tiene_acceso')}</p>
                        )}
                      </div>
                    </div>

                    <div className="border-t border-border pt-4 space-y-2">
                      <h3 className="text-sm font-medium text-muted-foreground">{t('añadir_usuario')}</h3>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={busqueda}
                          onChange={(e) => buscarUsuarios(e.target.value)}
                          placeholder={t('placeholder_usuario_o_email')}
                          className="input-field flex-1"
                        />
                        <select
                          value={nivelNuevo}
                          onChange={(e) => setNivelNuevo(e.target.value as 'ver' | 'comprar' | 'editar')}
                          className="input-field w-32"
                        >
                          <option value="editar">{t('editar')}</option>
                          <option value="comprar">{t('puede_comprar')}</option>
                          <option value="ver">{t('ver')}</option>
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

                    <button
                      onClick={() => setCompartiendoId(null)}
                      className="w-full px-3 py-2.5 bg-muted rounded-lg font-medium text-sm hover:bg-muted/80 transition-colors"
                    >
                      {t('cancelar')}
                    </button>
                  </div>
                )}

                {entrandoId === null && !esPropia && (
                  <button
                    onClick={() => setConfirmandoSalirId(confirmandoSalirId === hogar.id ? null : hogar.id)}
                    className="w-full mt-1 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors"
                  >
                    {confirmandoSalirId === hogar.id ? t('cancelar') : t('salir')}
                  </button>
                )}

                {confirmandoSalirId === hogar.id && !esPropia && (
                  <div className="card !p-4 mt-2 space-y-2 bg-red-50 dark:bg-red-950/30">
                    <p className="text-xs text-center text-red-600 dark:text-red-400 font-medium">{t('confirmar_salir_hogar')}</p>
                    <button
                      onClick={() => handleSalir(hogar.id)}
                      className="w-full px-3 py-2.5 bg-red-600 text-white rounded-lg font-medium text-sm hover:bg-red-700 transition-colors"
                    >
                      {t('salir')}
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {creando ? (
          <form onSubmit={handleCrear} className="card space-y-3">
            <input
              type="text"
              value={nombreNuevo}
              onChange={(e) => setNombreNuevo(e.target.value)}
              placeholder={t('placeholder_nombre_hogar')}
              className="input-field"
              autoFocus
              required
            />
            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">{t('crear_y_entrar')}</button>
              <button type="button" onClick={() => setCreando(false)} className="btn-secondary flex-1">{t('cancelar')}</button>
            </div>
          </form>
        ) : (
          <button
            onClick={() => setCreando(true)}
            className="w-full !p-3 rounded-2xl border-2 border-dashed border-border text-accent font-semibold text-sm flex items-center justify-center gap-2 hover:bg-muted/50 transition-colors"
          >
            <Plus className="w-4 h-4" /> {t('crear_hogar_nuevo')}
          </button>
        )}
      </div>

      {eligiendoIcono && (
        <IconPicker
          valorActual={iconoEditado}
          iconos={ICONOS_HOGAR}
          onSeleccionar={(icono) => {
            setIconoEditado(icono)
            setEligiendoIcono(false)
          }}
          onCerrar={() => setEligiendoIcono(false)}
        />
      )}
    </div>
  )
}
