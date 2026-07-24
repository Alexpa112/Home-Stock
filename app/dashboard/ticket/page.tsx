'use client'

import type { ChangeEvent } from 'react'
import { useState } from 'react'
import { Camera, Check, Loader, Upload } from 'lucide-react'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { tickets } from '@/lib/api'
import { getErrorMessage, parseNonNegativeInteger } from '@/lib/error-utils'
import type { TicketItem, TicketWarning } from '@/lib/types'

export default function EscanearTicketPage() {
  const [analizando, setAnalizando] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const [items, setItems] = useState<TicketItem[]>([])
  const [advertencias, setAdvertencias] = useState<TicketWarning[]>([])
  const [error, setError] = useState('')
  const [resultado, setResultado] = useState<{ creados: number; actualizados: number } | null>(null)

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setError('')
    setResultado(null)
    setAnalizando(true)

    try {
      const data: any = await tickets.analizar(file)
      setItems((data.items || []).map((item: TicketItem) => ({ ...item, incluir: true })))
      setAdvertencias(data.advertencias || [])
      if ((data.items || []).length === 0) {
        setError('No se detectó ningún producto en la imagen. Prueba con una foto más nítida y bien encuadrada.')
      }
    } catch (err) {
      setError(getErrorMessage(err, 'Error analizando el ticket'))
    } finally {
      setAnalizando(false)
      event.target.value = ''
    }
  }

  const actualizarItem = (index: number, cambios: Partial<TicketItem>) => {
    setItems((prev) => prev.map((item, currentIndex) => (currentIndex === index ? { ...item, ...cambios } : item)))
  }

  const handleConfirmar = async () => {
    const seleccionados = items.filter((item) => item.incluir && item.nombre.trim())
    if (seleccionados.length === 0) return

    try {
      setConfirmando(true)
      setError('')
      const data: any = await tickets.confirmar(
        seleccionados.map((item) => ({
          nombre: item.nombre,
          cantidad: item.cantidad,
          unidad: item.unidad,
          categoria: item.categoria,
          producto_id: item.producto_id,
        }))
      )
      setResultado(data)
      setItems([])
    } catch (err) {
      setError(getErrorMessage(err, 'Error importando los productos'))
    } finally {
      setConfirmando(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">Escanear Ticket</h1>
        <p className="text-muted-foreground mt-1">Haz una foto del ticket de compra y añade los productos al stock automáticamente</p>
      </div>

      {error && <StatusMessage variant="error" message={error} />}

      {resultado && (
        <StatusMessage
          variant="success"
          message={`Ticket importado: ${resultado.creados} producto(s) nuevo(s), ${resultado.actualizados} actualizado(s).`}
          className="items-center"
        />
      )}

      {items.length === 0 && !analizando && (
        <label className="card flex flex-col items-center justify-center gap-3 py-12 cursor-pointer border-2 border-dashed border-border hover:border-accent transition-colors">
          <Camera className="w-10 h-10 text-muted-foreground" />
          <span className="font-medium">Toca para hacer una foto o elegir una imagen</span>
          <span className="text-xs text-muted-foreground">JPG, PNG, hasta 10 MB</span>
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
          <span className="text-muted-foreground">Analizando ticket (OCR)... puede tardar un poco</span>
        </div>
      )}

      {advertencias.length > 0 && (
        <div className="space-y-2">
          {advertencias.map((advertencia, index) => (
            <StatusMessage key={index} variant="warning" message={advertencia.mensaje} />
          ))}
        </div>
      )}

      {items.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">{items.length} producto(s) detectado(s) — revisa antes de confirmar</h2>
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className={`card flex items-center gap-3 ${!item.incluir ? 'opacity-50' : ''} ${item.confianza_match < 0.7 ? 'border-yellow-400 dark:border-yellow-700' : ''}`}>
                <input
                  type="checkbox"
                  checked={item.incluir}
                  onChange={(e) => actualizarItem(index, { incluir: e.target.checked })}
                  className="w-5 h-5 flex-shrink-0"
                  aria-label="Incluir este producto"
                />
                <div className="flex-1 min-w-0 grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={item.nombre}
                    onChange={(e) => actualizarItem(index, { nombre: e.target.value })}
                    className="input-field !py-1.5 col-span-2"
                  />
                  <input
                    type="number"
                    value={item.cantidad}
                    min={0}
                    onChange={(e) => actualizarItem(index, { cantidad: parseNonNegativeInteger(e.target.value) })}
                    className="input-field !py-1.5"
                  />
                  <input
                    type="text"
                    value={item.categoria}
                    onChange={(e) => actualizarItem(index, { categoria: e.target.value })}
                    className="input-field !py-1.5"
                  />
                </div>
                {item.producto_id ? (
                  <Check className="w-5 h-5 text-green-500 flex-shrink-0" aria-label="Ya existe en el catálogo" />
                ) : (
                  <span className="text-xs text-muted-foreground flex-shrink-0">Nuevo</span>
                )}
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleConfirmar}
              disabled={confirmando || items.every((item) => !item.incluir)}
              className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {confirmando ? <Loader className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              Confirmar e importar al stock
            </button>
            <button onClick={() => setItems([])} className="btn-secondary">Cancelar</button>
          </div>
        </div>
      )}
    </div>
  )
}
