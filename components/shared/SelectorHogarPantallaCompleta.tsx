'use client'

import { useState } from 'react'
import { Home, Plus, Users, MoreVertical, X } from 'lucide-react'
import { useHogar } from '@/contexts/HogarContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { hogares as hogaresApi } from '@/lib/api'
import { clearCache } from '@/lib/dataCache'

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
  const { propios, compartidos, seleccionar, crear, refrescar } = useHogar()
  const { t } = useTranslation()
  const [entrandoId, setEntrandoId] = useState<number | null>(null)
  const [creando, setCreando] = useState(false)
  const [nombreNuevo, setNombreNuevo] = useState('')
  const [error, setError] = useState('')
  const [menuAbiertoId, setMenuAbiertoId] = useState<number | null>(null)
  const [renombrandoId, setRenombrandoId] = useState<number | null>(null)
  const [nombreEditado, setNombreEditado] = useState('')
  const [confirmandoEliminarId, setConfirmandoEliminarId] = useState<number | null>(null)
  const [confirmandoSalirId, setConfirmandoSalirId] = useState<number | null>(null)

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

  const iniciarRenombrar = (hogar: { id: number; nombre: string }) => {
    setMenuAbiertoId(null)
    setRenombrandoId(hogar.id)
    setNombreEditado(hogar.nombre)
  }

  const guardarRenombrar = async (id: number) => {
    if (!nombreEditado.trim()) {
      setRenombrandoId(null)
      return
    }
    try {
      await hogaresApi.actualizar(id, { nombre: nombreEditado.trim() })
      setRenombrandoId(null)
      await refrescar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_renombrar_lista'))
    }
  }

  const handleEliminar = async (id: number) => {
    if (confirmandoEliminarId !== id) {
      setMenuAbiertoId(null)
      setConfirmandoEliminarId(id)
      return
    }
    setConfirmandoEliminarId(null)
    try {
      await hogaresApi.eliminar(id)
      await refrescar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_lista'))
    }
  }

  const handleSalir = async (id: number) => {
    if (confirmandoSalirId !== id) {
      setMenuAbiertoId(null)
      setConfirmandoSalirId(id)
      return
    }
    setConfirmandoSalirId(null)
    try {
      await hogaresApi.salir(id)
      await refrescar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_error_al_salir_lista'))
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

        <div className="space-y-2">
          {hogares.map((hogar) => {
            const esPropia = propios.some((p) => p.id === hogar.id)
            return (
              <div key={hogar.id} className="card !p-3 flex items-center gap-3 relative">
                {renombrandoId === hogar.id ? (
                  <>
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-white" style={{ backgroundColor: hogar.color || '#B5551A' }}>
                      <Home className="w-5 h-5" />
                    </div>
                    <input
                      type="text"
                      value={nombreEditado}
                      onChange={(e) => setNombreEditado(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && guardarRenombrar(hogar.id)}
                      className="input-field !py-1.5 flex-1"
                      autoFocus
                    />
                    <button onClick={() => guardarRenombrar(hogar.id)} className="btn-secondary !py-1.5 !px-3 text-sm">{t('si')}</button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => handleEntrar(hogar.id)}
                      disabled={entrandoId !== null}
                      className="flex items-center gap-3 flex-1 min-w-0 text-left disabled:opacity-60"
                    >
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-white" style={{ backgroundColor: hogar.color || '#B5551A' }}>
                        <Home className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm truncate">{hogar.nombre}</p>
                        <p className="text-xs text-muted-foreground flex items-center gap-1">
                          {esPropia ? (
                            t('propietario_rol')
                          ) : (
                            <>
                              <Users className="w-3 h-3" /> {hogar.mi_rol === 'editar' ? t('compartida_puedes_editar') : t('compartida_solo_ver')}
                            </>
                          )}
                        </p>
                      </div>
                      {entrandoId === hogar.id && <span className="text-xs text-muted-foreground shrink-0">{t('entrando')}</span>}
                    </button>

                    {entrandoId === null && (
                      <button
                        onClick={() => setMenuAbiertoId(menuAbiertoId === hogar.id ? null : hogar.id)}
                        className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-muted shrink-0"
                        aria-label={t('mas_opciones')}
                      >
                        <MoreVertical className="w-4 h-4 text-muted-foreground" />
                      </button>
                    )}

                    {menuAbiertoId === hogar.id && (
                      <div
                        className="absolute right-2 top-12 z-10 bg-card border border-border rounded-xl shadow-lg overflow-hidden min-w-[9rem]"
                        onMouseLeave={() => setMenuAbiertoId(null)}
                      >
                        {esPropia ? (
                          <>
                            <button onClick={() => iniciarRenombrar(hogar)} className="w-full text-left px-3 py-2 text-sm hover:bg-muted">
                              {t('renombrar')}
                            </button>
                            {confirmandoEliminarId === hogar.id ? (
                              <div className="flex">
                                <button onClick={() => handleEliminar(hogar.id)} className="flex-1 px-3 py-2 text-sm font-semibold text-white bg-red-500">{t('si')}</button>
                                <button onClick={() => setConfirmandoEliminarId(null)} className="flex-1 px-3 py-2 text-sm bg-muted">{t('no')}</button>
                              </div>
                            ) : (
                              <button onClick={() => handleEliminar(hogar.id)} className="w-full text-left px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950">
                                {t('eliminar')}
                              </button>
                            )}
                          </>
                        ) : (
                          confirmandoSalirId === hogar.id ? (
                            <div className="flex">
                              <button onClick={() => handleSalir(hogar.id)} className="flex-1 px-3 py-2 text-sm font-semibold text-white bg-red-500">{t('salir')}</button>
                              <button onClick={() => setConfirmandoSalirId(null)} className="flex-1 px-3 py-2 text-sm bg-muted">{t('no')}</button>
                            </div>
                          ) : (
                            <button onClick={() => handleSalir(hogar.id)} className="w-full text-left px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950">
                              {t('salir')}
                            </button>
                          )
                        )}
                      </div>
                    )}
                  </>
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
    </div>
  )
}
