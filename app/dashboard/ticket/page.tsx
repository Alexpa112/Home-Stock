'use client'

import { useState } from 'react'
import { Camera, Upload, Check, AlertTriangle, Loader } from 'lucide-react'
import { tickets } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'

// Shape real: ver stockhogar/servicios/ocr/procesador_tickets_v2.py:crear_respuesta_usuario
interface ItemTicket {
  nombre: string
  cantidad: number
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
  const [resultado, setResultado] = useState<{ creados: number; actualizados: number } | null>(null)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setResultado(null)
    setAnalizando(true)
    try {
      const data: any = await tickets.analizar(file)
      const conIncluir = (data.items || []).map((it: ItemTicket) => ({ ...it, incluir: true }))
      setItems(conIncluir)
      setAdvertencias(data.advertencias || [])
      if ((data.items || []).length === 0) {
        setError(t('err_no_detecto_producto_imagen'))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_procesar'))
    } finally {
      setAnalizando(false)
      e.target.value = ''
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
          cantidad: it.cantidad,
          unidad: it.unidad,
          categoria: it.categoria,
          producto_id: it.producto_id,
        }))
      )
      setResultado(data)
      setItems([])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_importando_productos'))
    } finally {
      setConfirmando(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">{t('escanear_ticket_simple')}</h1>
        <p className="text-muted-foreground mt-1">
          {t('subtitulo_escanear_ticket')}
        </p>
      </div>

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
        <label className="card flex flex-col items-center justify-center gap-3 py-12 cursor-pointer border-2 border-dashed border-border hover:border-accent transition-colors">
          <Camera className="w-10 h-10 text-muted-foreground" />
          <span className="font-medium">{t('toca_para_foto')}</span>
          <span className="text-xs text-muted-foreground">{t('jpg_png_hasta_10mb')}</span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/jpg,image/gif,image/bmp"
            capture="environment"
            className="hidden"
            onChange={handleFile}
          />
        </label>
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
              className="text-sm text-accent hover:underline font-medium"
            >
              {items.every(i => i.incluir) ? t('deseleccionar_todos') : t('seleccionar_todos')}
            </button>
          </div>
          <div className="space-y-2">
            {items.map((item, idx) => (
              <div
                key={idx}
                className={`card !p-3 transition-opacity ${!item.incluir ? 'opacity-40' : ''} ${
                  item.confianza_match < 0.7 ? 'border-yellow-400 dark:border-yellow-700' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Checkbox con zona táctil grande */}
                  <button
                    onClick={() => actualizarItem(idx, { incluir: !item.incluir })}
                    className={`mt-1 w-6 h-6 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                      item.incluir
                        ? 'bg-accent border-accent'
                        : 'border-border bg-card'
                    }`}
                    aria-label={item.incluir ? t('aria_excluir_producto') : t('aria_incluir_producto')}
                  >
                    {item.incluir && <Check className="w-3.5 h-3.5 text-white" />}
                  </button>

                  <div className="flex-1 min-w-0 space-y-2">
                    <input
                      type="text"
                      value={item.nombre}
                      onChange={(e) => actualizarItem(idx, { nombre: e.target.value })}
                      className="input-field"
                      inputMode="text"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        value={item.cantidad}
                        min={0}
                        onChange={(e) => actualizarItem(idx, { cantidad: parseInt(e.target.value) || 0 })}
                        className="input-field"
                        inputMode="numeric"
                        placeholder={t('cantidad')}
                      />
                      <input
                        type="text"
                        value={item.categoria}
                        onChange={(e) => actualizarItem(idx, { categoria: e.target.value })}
                        className="input-field"
                        placeholder={t('categoria')}
                      />
                    </div>
                  </div>

                  <div className="flex-shrink-0 mt-1">
                    {item.producto_id ? (
                      <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400 font-medium">
                        <Check className="w-4 h-4" /> {t('conocido')}
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">{t('nuevo_badge')}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleConfirmar}
              disabled={confirmando || items.every((i) => !i.incluir)}
              className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {confirmando ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {t('confirmar_e_importar_stock')}
            </button>
            <button onClick={() => setItems([])} className="btn-secondary">
              {t('cancelar')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
