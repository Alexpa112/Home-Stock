'use client'

import { useState } from 'react'
import { Camera, FileUp, Upload, Check, AlertTriangle, Loader, Pencil } from 'lucide-react'
import { tickets } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'
import { CabeceraPantalla } from '@/components/dashboard/CabeceraPantalla'
import { accionesIrA } from '@/components/dashboard/accionesIrA'
import { suspenderPorEdicion, reanudarPorEdicion } from '@/lib/editSuspension'
import { cantidadDudosa, textoCantidad, formatearNumero } from '@/lib/ticket'

// Shape real: ver stockhogar/servicios/ocr/procesador_tickets_v2.py:crear_respuesta_usuario
interface ItemTicket {
  nombre: string
  cantidad: number | ''
  unidad: string
  categoria: string
  producto_id: number | null
  confianza_match: number
  confianza_cantidad: number
  precio_valido: boolean
  incluir?: boolean
}

export default function EscanearTicketPage() {
  const { t } = useTranslation()
  const [analizando, setAnalizando] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const [items, setItems] = useState<ItemTicket[]>([])
  const [advertencias, setAdvertencias] = useState<{ tipo: string; mensaje: string }[]>([])
  const [error, setError] = useState('')
  // Línea con el editor desplegado (lápiz de la revisión 6A).
  const [editando, setEditando] = useState<number | null>(null)
  const [resultado, setResultado] = useState<{ creados: number; actualizados: number } | null>(null)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setResultado(null)
    setItems([])
    setEditando(null)
    setAdvertencias([])
    setAnalizando(true)
    suspenderPorEdicion()
    try {
      const data: any = await tickets.analizar(file)
      const conIncluir = (data.items || []).map((it: ItemTicket) => ({ ...it, incluir: true }))
      setItems(conIncluir)
      setAdvertencias(data.advertencias || [])
      if ((data.items || []).length === 0) {
        setError(t('err_no_detecto_producto_imagen'))
      }
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : t('error_procesar')
      setError(mensaje)
      console.error('Error analizando ticket:', err)
    } finally {
      setAnalizando(false)
      e.target.value = ''
      reanudarPorEdicion()
    }
  }

  const actualizarItem = (idx: number, cambios: Partial<ItemTicket>) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...cambios } : it)))
  }

  const handleConfirmar = async () => {
    const seleccionados = items.filter((it) => it.incluir && it.nombre.trim())
    if (seleccionados.length === 0) return
    try {
      setConfirmando(true)
      setError('')
      const data: any = await tickets.confirmar(
        seleccionados.map((it) => ({
          nombre: it.nombre,
          cantidad: it.cantidad === '' ? 1 : it.cantidad,
          unidad: it.unidad,
          categoria: it.categoria,
          producto_id: it.producto_id,
        }))
      )
      setResultado(data)
      setItems([])
      setEditando(null)
      reanudarPorEdicion()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_importando_productos'))
    } finally {
      setConfirmando(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      <CabeceraPantalla
        titulo={t('escanear_ticket_simple')}
        subtitulo={t('subtitulo_escanear_ticket')}
        acciones={accionesIrA(t)}
      />

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg text-sm flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {resultado && (
        <div className="p-4 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-200 rounded-lg text-sm">
          {t('ticket_importado_resumen').replace('{creados}', String(resultado.creados)).replace('{actualizados}', String(resultado.actualizados))}{' '}
          <a href="/dashboard" className="underline font-medium">{t('ver_stock')}</a>
        </div>
      )}

      {items.length === 0 && !analizando && (
        <div className="card flex flex-col items-center justify-center gap-4 py-12 border-2 border-dashed border-border">
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <label className="btn-primary flex items-center justify-center gap-2 cursor-pointer">
              <Camera className="w-5 h-5" />
              {t('hacer_foto_boton')}
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/gif,image/bmp,image/webp,image/heic,image/heif"
                capture="environment"
                className="hidden"
                onChange={handleFile}
              />
            </label>
            <label className="btn-secondary flex items-center justify-center gap-2 cursor-pointer">
              <FileUp className="w-5 h-5" />
              {t('subir_archivo_boton')}
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/gif,image/bmp,image/webp,image/heic,image/heif,application/pdf"
                className="hidden"
                onChange={handleFile}
              />
            </label>
          </div>
          <span className="text-xs text-muted-foreground">{t('jpg_png_hasta_10mb')}</span>
        </div>
      )}

      {analizando && (
        <div className="card flex flex-col items-center justify-center gap-3 py-12">
          <Loader className="w-8 h-8 animate-spin text-accent" />
          <span className="text-muted-foreground">{t('analizando_ticket_ocr')}</span>
        </div>
      )}

      {advertencias.length > 0 && (
        <div className="space-y-2">
          {advertencias.map((a, i) => (
            <div key={i} className="p-3 bg-yellow-50 dark:bg-yellow-950 text-yellow-800 dark:text-yellow-200 rounded-lg text-sm flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{a.mensaje}</span>
            </div>
          ))}
        </div>
      )}

      {items.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold">{t('productos_detectados_contador').replace('{n}', String(items.length))}</h2>
            <button
              onClick={() => {
                const todosIncluidos = items.every(i => i.incluir)
                setItems(prev => prev.map(i => ({ ...i, incluir: !todosIncluidos })))
              }}
              className="min-h-[44px] px-2 text-sm text-accent hover:underline font-medium"
            >
              {items.every(i => i.incluir) ? t('deseleccionar_todos') : t('seleccionar_todos')}
            </button>
          </div>

          {/* Revisión en lista (rediseño 6A): cada línea con su casilla, sus
              chips y un lápiz que despliega la edición de nombre, cantidad y
              categoría. */}
          <div className="space-y-2">
            {items.map((item, idx) => {
              const dudosa = cantidadDudosa(item.cantidad, item.unidad)
              const editandoEsta = editando === idx
              return (
                <div
                  key={idx}
                  className={`card !p-3 transition-opacity ${!item.incluir ? 'opacity-50' : ''} ${
                    dudosa
                      ? 'border-amber-400 dark:border-amber-600'
                      : item.confianza_match < 0.7
                      ? 'border-yellow-400 dark:border-yellow-700'
                      : item.incluir
                      ? 'border-accent'
                      : ''
                  }`}
                >
                  <div className="flex items-start gap-1">
                    {/* Casilla con zona táctil de 44 px */}
                    <button
                      onClick={() => actualizarItem(idx, { incluir: !item.incluir })}
                      className="w-11 h-11 -mt-1 -ml-2 flex items-center justify-center flex-shrink-0"
                      aria-label={item.incluir ? t('aria_excluir_producto') : t('aria_incluir_producto')}
                      aria-pressed={item.incluir}
                    >
                      <span
                        className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-colors ${
                          item.incluir ? 'bg-accent border-accent' : 'border-border bg-card'
                        }`}
                      >
                        {item.incluir && <Check className="w-3.5 h-3.5 text-white" />}
                      </span>
                    </button>

                    <div className="flex-1 min-w-0 pt-0.5">
                      <p className="font-semibold text-sm break-words">{item.nombre || '—'}</p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                        {item.categoria && (
                          <span className="px-2.5 py-1 rounded-full bg-muted text-xs font-semibold text-muted-foreground">{item.categoria}</span>
                        )}
                        {item.cantidad !== '' && (
                          <span
                            className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                              dudosa ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200' : 'bg-muted text-muted-foreground'
                            }`}
                          >
                            {textoCantidad(item.cantidad, item.unidad)}
                          </span>
                        )}
                        {item.producto_id ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300 text-xs font-bold">
                            <Check className="w-3 h-3" /> {t('conocido')}
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200 text-xs font-bold">{t('nuevo_badge')}</span>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => setEditando(editandoEsta ? null : idx)}
                      className="w-11 h-11 -mt-1 -mr-2 flex items-center justify-center flex-shrink-0 rounded-xl hover:bg-muted"
                      aria-label={`${t('editar')} ${item.nombre}`}
                      aria-expanded={editandoEsta}
                    >
                      <Pencil className="w-4 h-4 text-muted-foreground" />
                    </button>
                  </div>

                  {dudosa && (
                    <p className="mt-2 flex items-start gap-2 text-xs text-amber-800 dark:text-amber-200" role="note">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                      <span>{t('aviso_cantidad_dudosa').replace('{cantidad}', formatearNumero(Number(item.cantidad)))}</span>
                    </p>
                  )}

                  {editandoEsta && (
                    <div className="mt-3 space-y-2">
                      <input
                        type="text"
                        value={item.nombre}
                        onChange={(e) => actualizarItem(idx, { nombre: e.target.value })}
                        className="input-field"
                        inputMode="text"
                        aria-label={t('nombre')}
                      />
                      <div className="grid grid-cols-2 gap-2">
                        {/* parseFloat, no parseInt: el escáner devuelve cantidades a
                            peso (0,850 kg) y con parseInt el usuario que tocaba el
                            campo las truncaba a 0, que es justo el dato que el
                            backend ya conserva. step="any" evita además que el
                            navegador marque el decimal como inválido. */}
                        <input
                          type="number"
                          value={item.cantidad}
                          min={0}
                          step="any"
                          onChange={(e) =>
                            actualizarItem(idx, {
                              cantidad: e.target.value === '' ? '' : parseFloat(e.target.value) || 0,
                            })
                          }
                          className="input-field"
                          inputMode="decimal"
                          placeholder={t('cantidad')}
                          aria-label={t('cantidad')}
                        />
                        <input
                          type="text"
                          value={item.categoria}
                          onChange={(e) => actualizarItem(idx, { categoria: e.target.value })}
                          className="input-field"
                          placeholder={t('categoria')}
                          aria-label={t('categoria')}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Hueco para que la barra fija (solo móvil) no tape la última línea. */}
          <div className="h-24 lg:hidden" aria-hidden="true" />
          {/* Barra de acción: fija sobre la barra de pestañas en móvil (no vale
              `sticky`: en móvil scrollea el documento y <main> tiene overflow, así
              que sticky lo tomaría como contenedor y flotaría sobre el contenido). */}
          <div className="fixed inset-x-0 bottom-[var(--mobile-toolbar-h)] z-[55] !mb-0 px-4 py-3 bg-card border-t border-border flex gap-2 lg:static lg:z-auto lg:p-0 lg:bg-transparent lg:border-0">
            <button
              onClick={() => { setItems([]); setEditando(null); reanudarPorEdicion() }}
              className="btn-secondary flex-1 min-h-[48px]"
            >
              {t('cancelar')}
            </button>
            <button
              onClick={handleConfirmar}
              disabled={confirmando || items.every((i) => !i.incluir)}
              className="btn-primary flex-[2] min-h-[48px] flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {confirmando ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {t('importar_n_al_stock').replace('{n}', String(items.filter((i) => i.incluir && i.nombre.trim()).length))}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
