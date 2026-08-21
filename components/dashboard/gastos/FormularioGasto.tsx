'use client'

import Link from 'next/link'
import { Plus, Paperclip } from 'lucide-react'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { RepartoParticipantes } from './RepartoParticipantes'

type ModoReparto = 'igual' | 'porcentaje' | 'partes' | 'personalizado'

interface CategoriaGasto {
  id: number
  nombre: string
  icono: string
}

interface Miembro {
  id: number
  nombre_usuario: string
}

export interface EstadoFormularioGasto {
  descripcion: string
  importe_total: string
  categoria: string | null
  fecha: string
  usuario_pagador_id: number | null
  seleccionados: Set<number>
  importesPorMiembro: Record<number, string>
  porcentajesPorMiembro: Record<number, string>
  partesPorMiembro: Record<number, string>
  modoReparto: ModoReparto
}

interface GastoEnEdicion {
  id: number
  tiene_recibo: boolean
}

interface FormularioGastoProps {
  id: string
  form: EstadoFormularioGasto
  miembros: Miembro[]
  categoriasGasto: CategoriaGasto[]
  simboloMoneda: string
  gastoEnEdicion?: GastoEnEdicion | null
  reciboUrl?: (id: number) => string
  onSubmit: (e: React.FormEvent) => void
  onCambiarDescripcion: (valor: string) => void
  onCambiarImporteTotal: (valor: string) => void
  onCambiarCategoria: (valor: string | null) => void
  onCambiarFecha: (valor: string) => void
  onCambiarPagador: (id: number) => void
  onToggleParticipante: (id: number) => void
  onCambiarModoReparto: (modo: ModoReparto) => void
  onCambiarPorcentajeParticipante: (id: number, valor: string) => void
  onCambiarPartesParticipante: (id: number, valor: string) => void
  onCambiarImporteParticipante: (id: number, valor: string) => void
  onSubirRecibo?: (id: number, file: File) => void
  onEliminarRecibo?: (id: number) => void
  t: (clave: string) => string
}

const TOLERANCIA_REPARTO = 0.01

// Opción 7A del rediseño de gastos (docs/REDISENO_GASTOS.md): importe
// protagonista, categoría en chips y sin scroll anidado (vive dentro de
// HojaCompleta, no de un Modal de altura limitada). El botón "Guardar" está
// en la cabecera de la hoja y referencia este <form> por id.
export function FormularioGasto({
  id,
  form,
  miembros,
  categoriasGasto,
  simboloMoneda,
  gastoEnEdicion,
  reciboUrl,
  onSubmit,
  onCambiarDescripcion,
  onCambiarImporteTotal,
  onCambiarCategoria,
  onCambiarFecha,
  onCambiarPagador,
  onToggleParticipante,
  onCambiarModoReparto,
  onCambiarPorcentajeParticipante,
  onCambiarPartesParticipante,
  onCambiarImporteParticipante,
  onSubirRecibo,
  onEliminarRecibo,
  t,
}: FormularioGastoProps) {
  const importeTotal = parseFloat(form.importe_total) || 0
  const sumaReparto = Array.from(form.seleccionados).reduce(
    (acc, uid) => acc + (parseFloat(form.importesPorMiembro[uid] || '0') || 0),
    0
  )
  const todosParticipanesConImporte = Array.from(form.seleccionados).every(
    (uid) => parseFloat(form.importesPorMiembro[uid] || '0') > 0
  )
  const reparteCuadra = form.seleccionados.size === 0 || (Math.abs(sumaReparto - importeTotal) <= TOLERANCIA_REPARTO && todosParticipanesConImporte)

  return (
    <form id={id} onSubmit={onSubmit} className="space-y-6">
      <div className="text-center space-y-1">
        <label htmlFor="gasto-importe" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t('importe_total')}
        </label>
        <div className="flex items-center justify-center gap-1">
          <input
            id="gasto-importe"
            type="number"
            inputMode="decimal"
            step="0.01"
            min="0.01"
            value={form.importe_total}
            onChange={(e) => onCambiarImporteTotal(e.target.value)}
            placeholder="0,00"
            required
            className="w-40 text-center text-4xl font-bold bg-transparent focus:outline-none tabular-nums"
          />
          <span className="text-2xl font-bold text-muted-foreground">{simboloMoneda}</span>
        </div>
      </div>

      <div>
        <input
          type="text"
          value={form.descripcion}
          onChange={(e) => onCambiarDescripcion(e.target.value)}
          placeholder={t('concepto_placeholder')}
          required
          className="input-field"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">{t('categoria')}</span>
          <Link href="/dashboard/gastos/categorias" className="text-sm text-accent hover:underline">
            {t('gestionar_categorias_gasto')}
          </Link>
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
          <button
            type="button"
            onClick={() => onCambiarCategoria(null)}
            className={`shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium border transition-colors ${
              form.categoria === null ? 'bg-accent text-accent-foreground border-accent' : 'bg-card text-muted-foreground border-border'
            }`}
          >
            {t('sin_categoria')}
          </button>
          {categoriasGasto.map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => onCambiarCategoria(cat.nombre)}
              className={`shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium border transition-colors ${
                form.categoria === cat.nombre ? 'bg-accent text-accent-foreground border-accent' : 'bg-card text-muted-foreground border-border'
              }`}
            >
              {cat.icono && <IconRenderer name={cat.icono} className="w-3.5 h-3.5" />}
              {cat.nombre}
            </button>
          ))}
          <Link
            href="/dashboard/gastos/categorias"
            className="shrink-0 flex items-center justify-center w-9 h-9 rounded-xl border border-dashed border-border text-muted-foreground"
            aria-label={t('gestionar_categorias_gasto')}
          >
            <Plus className="w-4 h-4" />
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="gasto-fecha" className="block text-sm font-medium mb-2">{t('fecha_gasto')}</label>
          <input
            id="gasto-fecha"
            type="date"
            value={form.fecha}
            onChange={(e) => onCambiarFecha(e.target.value)}
            required
            className="input-field"
          />
        </div>
        <div>
          <label htmlFor="gasto-pagador" className="block text-sm font-medium mb-2">{t('pagado_por')}</label>
          <select
            id="gasto-pagador"
            value={form.usuario_pagador_id ?? ''}
            onChange={(e) => onCambiarPagador(Number(e.target.value))}
            className="input-field"
          >
            <option value="" disabled>—</option>
            {miembros.map((m) => (
              <option key={m.id} value={m.id}>{m.nombre_usuario}</option>
            ))}
          </select>
        </div>
      </div>

      <RepartoParticipantes
        miembros={miembros}
        seleccionados={form.seleccionados}
        modoReparto={form.modoReparto}
        importesPorMiembro={form.importesPorMiembro}
        porcentajesPorMiembro={form.porcentajesPorMiembro}
        partesPorMiembro={form.partesPorMiembro}
        simboloMoneda={simboloMoneda}
        reparteCuadra={reparteCuadra}
        onToggle={onToggleParticipante}
        onCambiarModo={onCambiarModoReparto}
        onCambiarPorcentaje={onCambiarPorcentajeParticipante}
        onCambiarPartes={onCambiarPartesParticipante}
        onCambiarImporte={onCambiarImporteParticipante}
        etiquetaParticipantes={t('participantes')}
        etiquetaIgual={t('dividir_partes_iguales')}
        etiquetaPorcentaje={t('dividir_por_porcentaje')}
        etiquetaPartes={t('dividir_por_partes')}
        etiquetaPersonalizado={t('dividir_personalizado')}
        etiquetaExcluido={t('excluido')}
        etiquetaCuadra={t('reparto_cuadra')}
        etiquetaNoCuadra={t('reparto_no_cuadra')}
      />

      {gastoEnEdicion && reciboUrl && (
        <div className="space-y-2">
          <span className="text-sm font-medium">{t('recibo')}</span>
          {gastoEnEdicion.tiene_recibo ? (
            <div className="flex items-center gap-3">
              <a
                href={reciboUrl(gastoEnEdicion.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent hover:underline flex items-center gap-1"
              >
                <Paperclip className="w-4 h-4" /> {t('ver_recibo')}
              </a>
              <button
                type="button"
                onClick={() => onEliminarRecibo?.(gastoEnEdicion.id)}
                className="text-sm text-red-500 hover:underline"
              >
                {t('eliminar')}
              </button>
            </div>
          ) : (
            <input
              type="file"
              accept="image/*"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) onSubirRecibo?.(gastoEnEdicion.id, file)
              }}
              className="text-sm"
            />
          )}
        </div>
      )}
    </form>
  )
}
