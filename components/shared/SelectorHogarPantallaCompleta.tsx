'use client'

import { useState } from 'react'
import { Home, Plus, Users, X } from 'lucide-react'
import { useHogar } from '@/contexts/HogarContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { listas as listasApi } from '@/lib/api'
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
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [nombreEditado, setNombreEditado] = useState('')
  const [colorEditado, setColorEditado] = useState('')
  const [confirmandoEliminarId, setConfirmandoEliminarId] = useState<number | null>(null)
  const [confirmandoSalirId, setConfirmandoSalirId] = useState<number | null>(null)
  const [coloresDisponibles] = useState(['#B5551A', '#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6', '#1ABC9C', '#34495E'])

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

  const iniciarEdicion = (hogar: { id: number; nombre: string; color?: string }) => {
    setEditandoId(hogar.id)
    setNombreEditado(hogar.nombre)
    setColorEditado(hogar.color || '#B5551A')
  }

  const guardarEdicion = async (id: number) => {
    if (!nombreEditado.trim()) {
      setEditandoId(null)
      return
    }
    try {
      await listasApi.actualizar(id, { nombre: nombreEditado.trim(), color: colorEditado })
      setEditandoId(null)
      await refrescar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_renombrar_lista'))
    }
  }

  const handleEliminar = async (id: number) => {
    if (confirmandoEliminarId !== id) {
      setConfirmandoEliminarId(id)
      return
    }
    setConfirmandoEliminarId(null)
    try {
      await listasApi.eliminar(id)
      await refrescar()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_lista'))
    }
  }

  const handleSalir = async (id: number) => {
    if (confirmandoSalirId !== id) {
      setConfirmandoSalirId(id)
      return
    }
    setConfirmandoSalirId(null)
    try {
      await listasApi.salir(id)
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

                {entrandoId === null && esPropia && (
                  <button
                    onClick={() => editando ? setEditandoId(null) : iniciarEdicion(hogar)}
                    className="w-full mt-1 px-3 py-2 text-sm text-muted-foreground hover:text-accent hover:bg-muted rounded-lg transition-colors"
                  >
                    {editando ? t('cancelar') : t('editar')}
                  </button>
                )}

                {editando && esPropia && (
                  <div className="card !p-4 mt-2 space-y-4 bg-muted/30">
                    <div>
                      <label className="text-xs font-semibold text-muted-foreground block mb-2">{t('nombre')}</label>
                      <input
                        type="text"
                        value={nombreEditado}
                        onChange={(e) => setNombreEditado(e.target.value)}
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

                    <div className="border-t border-border pt-4 space-y-2">
                      <button
                        onClick={() => guardarEdicion(hogar.id)}
                        className="w-full px-3 py-2.5 bg-accent text-white rounded-lg font-medium text-sm hover:bg-accent/90 transition-colors"
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
    </div>
  )
}
