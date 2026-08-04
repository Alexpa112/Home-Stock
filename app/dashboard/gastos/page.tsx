'use client'

import { useState, useEffect } from 'react'
import { Plus, Trash2, Pencil, AlertCircle, Receipt, HandCoins, Download, Tags, X } from 'lucide-react'
import { Modal } from '@/components/dashboard/Modal'
import { IconPicker } from '@/components/dashboard/IconPicker'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { BarraHorizontal } from '@/components/dashboard/BarraHorizontal'
import { GraficoColumnas } from '@/components/dashboard/GraficoColumnas'
import { gastos as gastosApi, hogares as hogaresApi, categoriasGasto as categoriasGastoApi } from '@/lib/api'
import { useHogar } from '@/contexts/HogarContext'
import { useTranslation } from '@/contexts/TranslationContext'
import { getCached, setCached } from '@/lib/dataCache'
import { usePollingRefresh } from '@/lib/usePollingRefresh'
import { formatImporte } from '@/lib/format'
import { SkeletonCards } from '@/components/dashboard/SkeletonCards'
import { totalesPorCategoria, evolucionMensual, balancePorPersona } from '@/lib/gastosStats'

const CACHE_KEY_GASTOS = 'gastos:lista'
const CACHE_KEY_SALDO = 'gastos:saldo'
const CACHE_KEY_SUGERENCIAS = 'gastos:sugerencias'
const CACHE_KEY_CATEGORIAS_GASTO = 'gastos:categorias'

interface Participante {
  usuario_id: number
  importe: number
  nombre_usuario: string
}

interface Gasto {
  id: number
  descripcion: string
  importe_total: number
  fecha: string
  categoria?: string | null
  usuario_pagador_id: number
  pagador_nombre: string
  participantes: Participante[]
}

interface CategoriaGasto {
  id: number
  nombre: string
  icono: string
}

interface SaldoItem {
  usuario_id: number
  nombre_usuario: string
  saldo: number
}

interface SugerenciaPago {
  usuario_origen_id: number
  usuario_origen_nombre: string
  usuario_destino_id: number
  usuario_destino_nombre: string
  importe: number
}

interface Miembro {
  id: number
  nombre_usuario: string
}

type ModoReparto = 'igual' | 'porcentaje' | 'personalizado'

interface FormularioGasto {
  descripcion: string
  importe_total: string
  categoria: string | null
  usuario_pagador_id: number | null
  seleccionados: Set<number>
  importesPorMiembro: Record<number, string>
  porcentajesPorMiembro: Record<number, string>
  modoReparto: ModoReparto
}

const FORM_VACIO = (pagadorPorDefecto: number | null): FormularioGasto => ({
  descripcion: '',
  importe_total: '',
  categoria: null,
  usuario_pagador_id: pagadorPorDefecto,
  seleccionados: new Set(pagadorPorDefecto ? [pagadorPorDefecto] : []),
  importesPorMiembro: {},
  porcentajesPorMiembro: {},
  modoReparto: 'igual',
})

export default function GastosPage() {
  const { t } = useTranslation()
  const { hogarActivoId, propios, compartidos } = useHogar()

  const hogarActivo = [...propios, ...compartidos].find((h: any) => h.id === hogarActivoId)
  const simboloMoneda = hogarActivo?.simbolo_moneda || '€'

  const [gastos, setGastos] = useState<Gasto[]>(() => getCached<Gasto[]>(CACHE_KEY_GASTOS) || [])
  const [saldo, setSaldo] = useState<SaldoItem[]>(() => getCached<SaldoItem[]>(CACHE_KEY_SALDO) || [])
  const [sugerencias, setSugerencias] = useState<SugerenciaPago[]>(
    () => getCached<SugerenciaPago[]>(CACHE_KEY_SUGERENCIAS) || []
  )
  const [miembros, setMiembros] = useState<Miembro[]>([])
  const [categoriasGasto, setCategoriasGasto] = useState<CategoriaGasto[]>(
    () => getCached<CategoriaGasto[]>(CACHE_KEY_CATEGORIAS_GASTO) || []
  )
  const [loading, setLoading] = useState(gastos.length === 0)
  const [error, setError] = useState('')
  const [confirmandoId, setConfirmandoId] = useState<number | null>(null)
  const [vista, setVista] = useState<'gastos' | 'estadisticas'>('gastos')

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<FormularioGasto>(FORM_VACIO(null))
  const [modalEdicionId, setModalEdicionId] = useState<number | null>(null)

  const [gestionandoCategoriasGasto, setGestionandoCategoriasGasto] = useState(false)
  const [nuevaCategoriaGasto, setNuevaCategoriaGasto] = useState('')
  const [nuevaCategoriaGastoIcono, setNuevaCategoriaGastoIcono] = useState<string | undefined>(undefined)
  const [mostrarIconPickerCategoriaGasto, setMostrarIconPickerCategoriaGasto] = useState(false)
  const [confirmandoEliminarCatGastoId, setConfirmandoEliminarCatGastoId] = useState<number | null>(null)

  const [showLiquidacion, setShowLiquidacion] = useState(false)
  const [liquidacion, setLiquidacion] = useState({ usuario_origen_id: null as number | null, usuario_destino_id: null as number | null, importe: '', nota: '' })

  const abrirLiquidacionSugerida = (s: SugerenciaPago) => {
    setLiquidacion({ usuario_origen_id: s.usuario_origen_id, usuario_destino_id: s.usuario_destino_id, importe: s.importe.toFixed(2), nota: '' })
    setShowLiquidacion(true)
  }

  const cargarDatos = async () => {
    try {
      setError('')
      const [gastosData, saldoData, sugerenciasData] = await Promise.all([
        gastosApi.listar(), gastosApi.saldo(), gastosApi.simplificar(),
      ])
      const gastosArr = Array.isArray(gastosData) ? gastosData : []
      const saldoArr = Array.isArray(saldoData) ? saldoData : []
      const sugerenciasArr = Array.isArray(sugerenciasData) ? sugerenciasData : []
      setGastos(gastosArr)
      setSaldo(saldoArr)
      setSugerencias(sugerenciasArr)
      setCached(CACHE_KEY_GASTOS, gastosArr)
      setCached(CACHE_KEY_SALDO, saldoArr)
      setCached(CACHE_KEY_SUGERENCIAS, sugerenciasArr)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_conexion_titulo'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargarDatos()
  }, [])

  useEffect(() => {
    if (!hogarActivoId) return
    hogaresApi.miembrosBasico(hogarActivoId).then((data: any) => {
      setMiembros(Array.isArray(data) ? data : [])
    }).catch(() => {})
  }, [hogarActivoId])

  useEffect(() => {
    categoriasGastoApi.listar().then((data: any) => {
      const arr = Array.isArray(data) ? data : []
      setCategoriasGasto(arr)
      setCached(CACHE_KEY_CATEGORIAS_GASTO, arr)
    }).catch(() => {})
  }, [])

  usePollingRefresh(
    () => cargarDatos(),
    () => showForm || modalEdicionId !== null || showLiquidacion || gestionandoCategoriasGasto
  )

  const getCategoriaGastoIcon = (nombre: string | null | undefined) => {
    if (!nombre) return null
    return categoriasGasto.find((c) => c.nombre === nombre)?.icono || null
  }

  const aplicarModoReparto = (siguiente: FormularioGasto): FormularioGasto => {
    const importeTotal = parseFloat(siguiente.importe_total) || 0
    const ids = Array.from(siguiente.seleccionados)
    if (ids.length === 0) return siguiente

    if (siguiente.modoReparto === 'igual') {
      const porCabeza = Math.round((importeTotal / ids.length) * 100) / 100
      const importesPorMiembro: Record<number, string> = {}
      ids.forEach((id) => { importesPorMiembro[id] = porCabeza.toFixed(2) })
      return { ...siguiente, importesPorMiembro }
    }

    if (siguiente.modoReparto === 'porcentaje') {
      const importesPorMiembro: Record<number, string> = {}
      let acumulado = 0
      ids.forEach((id, idx) => {
        if (idx === ids.length - 1) {
          importesPorMiembro[id] = (Math.round((importeTotal - acumulado) * 100) / 100).toFixed(2)
        } else {
          const pct = parseFloat(siguiente.porcentajesPorMiembro[id] || '0') || 0
          const importe = Math.round(importeTotal * pct) / 100
          acumulado += importe
          importesPorMiembro[id] = importe.toFixed(2)
        }
      })
      return { ...siguiente, importesPorMiembro }
    }

    return siguiente
  }

  const toggleParticipante = (id: number) => {
    setForm((prev) => {
      const seleccionados = new Set(prev.seleccionados)
      if (seleccionados.has(id)) {
        seleccionados.delete(id)
      } else {
        seleccionados.add(id)
      }
      return aplicarModoReparto({ ...prev, seleccionados })
    })
  }

  const cambiarImporteTotal = (valor: string) => {
    setForm((prev) => aplicarModoReparto({ ...prev, importe_total: valor }))
  }

  const cambiarModoReparto = (modo: ModoReparto) => {
    setForm((prev) => aplicarModoReparto({ ...prev, modoReparto: modo }))
  }

  const cambiarPorcentajeParticipante = (id: number, valor: string) => {
    setForm((prev) => aplicarModoReparto({
      ...prev,
      modoReparto: 'porcentaje',
      porcentajesPorMiembro: { ...prev.porcentajesPorMiembro, [id]: valor },
    }))
  }

  const cambiarImporteParticipante = (id: number, valor: string) => {
    setForm((prev) => ({
      ...prev,
      modoReparto: 'personalizado',
      importesPorMiembro: { ...prev.importesPorMiembro, [id]: valor },
    }))
  }

  const abrirModalNuevo = () => {
    setForm(FORM_VACIO(null))
    setShowForm(true)
  }

  const abrirModalEdicion = (gasto: Gasto) => {
    const seleccionados = new Set(gasto.participantes.map((p) => p.usuario_id))
    const importesPorMiembro: Record<number, string> = {}
    gasto.participantes.forEach((p) => {
      importesPorMiembro[p.usuario_id] = p.importe.toFixed(2)
    })
    setForm({
      descripcion: gasto.descripcion,
      importe_total: gasto.importe_total.toFixed(2),
      categoria: gasto.categoria ?? null,
      usuario_pagador_id: gasto.usuario_pagador_id,
      seleccionados,
      importesPorMiembro,
      porcentajesPorMiembro: {},
      modoReparto: 'personalizado',
    })
    setModalEdicionId(gasto.id)
  }

  const handleCrearCategoriaGasto = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!nuevaCategoriaGasto.trim()) return
    try {
      setError('')
      await categoriasGastoApi.crear(nuevaCategoriaGasto.trim(), nuevaCategoriaGastoIcono)
      setNuevaCategoriaGasto('')
      setNuevaCategoriaGastoIcono(undefined)
      const data: any = await categoriasGastoApi.listar()
      const arr = Array.isArray(data) ? data : []
      setCategoriasGasto(arr)
      setCached(CACHE_KEY_CATEGORIAS_GASTO, arr)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_crear_categoria'))
    }
  }

  const handleEliminarCategoriaGasto = async (id: number) => {
    if (confirmandoEliminarCatGastoId !== id) { setConfirmandoEliminarCatGastoId(id); return }
    setConfirmandoEliminarCatGastoId(null)
    try {
      setError('')
      await categoriasGastoApi.eliminar(id)
      const data: any = await categoriasGastoApi.listar()
      const arr = Array.isArray(data) ? data : []
      setCategoriasGasto(arr)
      setCached(CACHE_KEY_CATEGORIAS_GASTO, arr)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_categoria_uso'))
    }
  }

  const handleExportarCsv = async () => {
    try {
      setError('')
      await gastosApi.exportarCsv()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error_conexion_titulo'))
    }
  }

  const construirParticipantes = () =>
    Array.from(form.seleccionados).map((usuario_id) => ({
      usuario_id,
      importe: parseFloat(form.importesPorMiembro[usuario_id] || '0') || 0,
    }))

  const handleGuardar = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.usuario_pagador_id || form.seleccionados.size === 0) return

    const datos = {
      descripcion: form.descripcion.trim(),
      importe_total: parseFloat(form.importe_total) || 0,
      categoria: form.categoria,
      usuario_pagador_id: form.usuario_pagador_id,
      participantes: construirParticipantes(),
    }

    try {
      setError('')
      if (modalEdicionId !== null) {
        await gastosApi.actualizar(modalEdicionId, datos)
      } else {
        await gastosApi.crear(datos)
      }
      setShowForm(false)
      setModalEdicionId(null)
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_actualizar'))
    }
  }

  const handleEliminar = async (id: number) => {
    if (confirmandoId !== id) {
      setConfirmandoId(id)
      return
    }
    setConfirmandoId(null)
    try {
      setError('')
      await gastosApi.eliminar(id)
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_articulo'))
    }
  }

  const handleRegistrarLiquidacion = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!liquidacion.usuario_origen_id || !liquidacion.usuario_destino_id) return
    try {
      setError('')
      await gastosApi.registrarLiquidacion({
        usuario_origen_id: liquidacion.usuario_origen_id,
        usuario_destino_id: liquidacion.usuario_destino_id,
        importe: parseFloat(liquidacion.importe) || 0,
        nota: liquidacion.nota.trim() || undefined,
      })
      setShowLiquidacion(false)
      setLiquidacion({ usuario_origen_id: null, usuario_destino_id: null, importe: '', nota: '' })
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_actualizar'))
    }
  }

  const renderFormularioGasto = () => (
    <form onSubmit={handleGuardar} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-2">{t('descripcion')}</label>
        <input
          type="text"
          value={form.descripcion}
          onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
          className="input-field"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">{t('importe_total')}</label>
        <input
          type="number"
          step="0.01"
          min="0.01"
          value={form.importe_total}
          onChange={(e) => cambiarImporteTotal(e.target.value)}
          className="input-field"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">{t('pagado_por')}</label>
        <select
          value={form.usuario_pagador_id ?? ''}
          onChange={(e) => setForm({ ...form, usuario_pagador_id: Number(e.target.value) })}
          className="input-field"
          required
        >
          <option value="" disabled>—</option>
          {miembros.map((m) => (
            <option key={m.id} value={m.id}>{m.nombre_usuario}</option>
          ))}
        </select>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium">{t('categoria')}</label>
          <button
            type="button"
            onClick={() => setGestionandoCategoriasGasto(!gestionandoCategoriasGasto)}
            className="text-sm text-accent hover:underline flex items-center gap-1"
          >
            <Tags className="w-4 h-4" /> {t('categorias')}
          </button>
        </div>

        {gestionandoCategoriasGasto && (
          <div className="p-3 bg-muted rounded-lg space-y-2 mb-2">
            <div className="flex flex-wrap gap-2">
              {categoriasGasto.map((cat) => (
                confirmandoEliminarCatGastoId === cat.id ? (
                  <span key={cat.id} className="flex items-center gap-1 px-2 py-1 bg-card rounded-full text-xs border border-red-300 dark:border-red-700">
                    <span className="text-red-600 dark:text-red-400 mr-0.5">{t('eliminar_pregunta')}</span>
                    <button type="button" onClick={() => handleEliminarCategoriaGasto(cat.id)} className="px-1.5 py-0.5 text-white bg-red-500 rounded-md font-medium">{t('si')}</button>
                    <button type="button" onClick={() => setConfirmandoEliminarCatGastoId(null)} className="px-1.5 py-0.5 bg-muted rounded-md font-medium">{t('no')}</button>
                  </span>
                ) : (
                  <span key={cat.id} className="flex items-center gap-1 px-2 py-1 bg-card rounded-full text-xs border border-border">
                    {cat.nombre}
                    <button type="button" onClick={() => handleEliminarCategoriaGasto(cat.id)} aria-label={`${t('eliminar')} ${cat.nombre}`}>
                      <X className="w-3 h-3 text-red-500" />
                    </button>
                  </span>
                )
              ))}
            </div>
            <form onSubmit={handleCrearCategoriaGasto} className="flex gap-2">
              <button
                type="button"
                onClick={() => setMostrarIconPickerCategoriaGasto(true)}
                className="w-9 h-9 shrink-0 rounded-lg bg-card border border-border flex items-center justify-center"
                aria-label={t('cambiar_icono')}
              >
                {nuevaCategoriaGastoIcono ? (
                  <IconRenderer name={nuevaCategoriaGastoIcono} className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <Tags className="w-4 h-4 text-muted-foreground" />
                )}
              </button>
              <input
                type="text"
                value={nuevaCategoriaGasto}
                onChange={(e) => setNuevaCategoriaGasto(e.target.value)}
                placeholder={t('nueva_categoria')}
                className="input-field !py-1.5 flex-1"
              />
              <button type="submit" className="btn-secondary !py-1.5">{t('añadir')}</button>
            </form>
          </div>
        )}

        <select
          value={form.categoria ?? ''}
          onChange={(e) => setForm({ ...form, categoria: e.target.value || null })}
          className="input-field"
        >
          <option value="">{t('sin_categoria')}</option>
          {categoriasGasto.map((cat) => (
            <option key={cat.id} value={cat.nombre}>{cat.nombre}</option>
          ))}
        </select>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium">{t('participantes')}</label>
          <div className="flex gap-1">
            {(['igual', 'porcentaje', 'personalizado'] as const).map((modo) => (
              <button
                key={modo}
                type="button"
                onClick={() => cambiarModoReparto(modo)}
                className={`px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
                  form.modoReparto === modo ? 'bg-primary text-white' : 'bg-muted text-muted-foreground'
                }`}
              >
                {t(modo === 'igual' ? 'dividir_partes_iguales' : modo === 'porcentaje' ? 'dividir_por_porcentaje' : 'dividir_personalizado')}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          {miembros.map((m) => (
            <div key={m.id} className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={form.seleccionados.has(m.id)}
                onChange={() => toggleParticipante(m.id)}
              />
              <span className="flex-1 text-sm truncate">{m.nombre_usuario}</span>
              {form.modoReparto === 'porcentaje' ? (
                <>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    disabled={!form.seleccionados.has(m.id)}
                    value={form.porcentajesPorMiembro[m.id] ?? ''}
                    onChange={(e) => cambiarPorcentajeParticipante(m.id, e.target.value)}
                    className="input-field !py-1 !px-2 w-16 text-sm"
                  />
                  <span className="text-xs text-muted-foreground w-16 text-right flex-shrink-0">
                    {formatImporte(parseFloat(form.importesPorMiembro[m.id] || '0') || 0, simboloMoneda)}
                  </span>
                </>
              ) : (
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  disabled={!form.seleccionados.has(m.id)}
                  value={form.importesPorMiembro[m.id] ?? ''}
                  onChange={(e) => cambiarImporteParticipante(m.id, e.target.value)}
                  className="input-field !py-1 !px-2 w-24 text-sm"
                />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <button type="submit" className="btn-primary flex-1">{t('guardar')}</button>
        <button
          type="button"
          onClick={() => { setShowForm(false); setModalEdicionId(null) }}
          className="btn-secondary flex-1"
        >
          {t('cancelar')}
        </button>
      </div>
    </form>
  )

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-6 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold flex items-center gap-2">
            <Receipt className="w-7 h-7" /> {t('nav_gastos')}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExportarCsv} className="btn-secondary flex items-center gap-2 min-h-[44px]">
            <Download className="w-5 h-5" />
            <span className="hidden sm:inline">{t('exportar_csv')}</span>
          </button>
          <button onClick={() => setShowLiquidacion(true)} className="btn-secondary flex items-center gap-2 min-h-[44px]">
            <HandCoins className="w-5 h-5" />
            <span className="hidden sm:inline">{t('registrar_pago')}</span>
          </button>
          <button onClick={abrirModalNuevo} className="btn-primary flex items-center gap-2 min-h-[44px]">
            <Plus className="w-5 h-5" />
            <span className="hidden sm:inline">{t('nuevo_gasto')}</span>
          </button>
        </div>
      </div>

      <div className="flex gap-1">
        {(['gastos', 'estadisticas'] as const).map((v) => (
          <button
            key={v}
            onClick={() => setVista(v)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              vista === v ? 'bg-primary text-white' : 'bg-muted text-muted-foreground'
            }`}
          >
            {t(v === 'gastos' ? 'nav_gastos' : 'estadisticas')}
          </button>
        ))}
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {vista === 'gastos' ? (
        <>
          {saldo.length > 0 && (
            <div className="card space-y-2">
              <h2 className="text-lg font-semibold">{t('saldo_neto')}</h2>
              <div className="space-y-2">
                {saldo.map((s) => (
                  <div key={s.usuario_id} className="flex items-center justify-between text-sm">
                    <span className="truncate">{s.nombre_usuario}</span>
                    <span className={s.saldo > 0 ? 'text-green-600 font-medium' : s.saldo < 0 ? 'text-red-600 font-medium' : 'text-muted-foreground'}>
                      {s.saldo === 0
                        ? formatImporte(0, simboloMoneda)
                        : `${s.saldo > 0 ? t('le_deben') : t('debe')}: ${formatImporte(Math.abs(s.saldo), simboloMoneda)}`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {sugerencias.length > 0 && (
            <div className="card space-y-2">
              <h2 className="text-lg font-semibold">{t('pagos_sugeridos')}</h2>
              <div className="space-y-2">
                {sugerencias.map((s, idx) => (
                  <div key={idx} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">
                      {s.usuario_origen_nombre} → {s.usuario_destino_nombre}: {formatImporte(s.importe, simboloMoneda)}
                    </span>
                    <button
                      onClick={() => abrirLiquidacionSugerida(s)}
                      className="btn-secondary shrink-0 px-3 py-1.5 text-xs"
                    >
                      {t('pagar')}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {loading ? (
            <SkeletonCards />
          ) : gastos.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">{t('sin_gastos_aun')}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {gastos.map((gasto) => {
                const iconoCategoria = getCategoriaGastoIcon(gasto.categoria)
                return (
                <div key={gasto.id} className="card flex items-center justify-between gap-4">
                  {iconoCategoria && (
                    <IconRenderer name={iconoCategoria} className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate">{gasto.descripcion}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatImporte(gasto.importe_total, simboloMoneda)} · {t('pagado_por')} {gasto.pagador_nombre}
                    </p>
                  </div>
                  <button
                    onClick={() => abrirModalEdicion(gasto)}
                    className="w-10 h-10 flex items-center justify-center hover:bg-muted rounded-xl transition-colors flex-shrink-0"
                    aria-label={t('editar')}
                  >
                    <Pencil className="w-4 h-4 text-muted-foreground" />
                  </button>
                  {confirmandoId === gasto.id ? (
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button onClick={() => handleEliminar(gasto.id)} className="px-2 h-10 text-xs font-semibold text-white bg-red-500 rounded-xl">{t('si')}</button>
                      <button onClick={() => setConfirmandoId(null)} className="px-2 h-10 text-xs font-semibold text-foreground bg-muted rounded-xl">{t('no')}</button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleEliminar(gasto.id)}
                      className="w-10 h-10 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors flex-shrink-0"
                      aria-label={t('eliminar')}
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  )}
                </div>
                )
              })}
            </div>
          )}
        </>
      ) : gastos.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">{t('sin_datos_estadisticas')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="card space-y-3">
            <h2 className="text-lg font-semibold">{t('gasto_total_por_categoria')}</h2>
            <BarraHorizontal
              datos={totalesPorCategoria(gastos, t('sin_categoria'))}
              formatearValor={(v) => formatImporte(v, simboloMoneda)}
            />
          </div>
          <div className="card space-y-3">
            <h2 className="text-lg font-semibold">{t('evolucion_mensual')}</h2>
            <GraficoColumnas
              datos={evolucionMensual(gastos, 12)}
              formatearValor={(v) => formatImporte(v, simboloMoneda)}
            />
          </div>
          <div className="card space-y-3">
            <h2 className="text-lg font-semibold">{t('balance_por_persona')}</h2>
            <BarraHorizontal
              datos={balancePorPersona(saldo)}
              diverging
              formatearValor={(v) => formatImporte(v, simboloMoneda)}
            />
          </div>
        </div>
      )}

      {mostrarIconPickerCategoriaGasto && (
        <IconPicker
          valorActual={nuevaCategoriaGastoIcono}
          onSeleccionar={(icono) => {
            setNuevaCategoriaGastoIcono(icono)
            setMostrarIconPickerCategoriaGasto(false)
          }}
          onCerrar={() => setMostrarIconPickerCategoriaGasto(false)}
        />
      )}

      {(showForm || modalEdicionId !== null) && (
        <Modal onCerrar={() => { setShowForm(false); setModalEdicionId(null) }}>
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{modalEdicionId !== null ? t('editar_gasto') : t('nuevo_gasto')}</h2>
            {renderFormularioGasto()}
          </div>
        </Modal>
      )}

      {showLiquidacion && (
        <Modal onCerrar={() => setShowLiquidacion(false)}>
          <form onSubmit={handleRegistrarLiquidacion} className="space-y-4">
            <h2 className="text-lg font-semibold">{t('registrar_pago')}</h2>

            <div>
              <label className="block text-sm font-medium mb-2">{t('pagado_por')}</label>
              <select
                value={liquidacion.usuario_origen_id ?? ''}
                onChange={(e) => setLiquidacion({ ...liquidacion, usuario_origen_id: Number(e.target.value) })}
                className="input-field"
                required
              >
                <option value="" disabled>—</option>
                {miembros.map((m) => (
                  <option key={m.id} value={m.id}>{m.nombre_usuario}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t('le_deben')}</label>
              <select
                value={liquidacion.usuario_destino_id ?? ''}
                onChange={(e) => setLiquidacion({ ...liquidacion, usuario_destino_id: Number(e.target.value) })}
                className="input-field"
                required
              >
                <option value="" disabled>—</option>
                {miembros.filter((m) => m.id !== liquidacion.usuario_origen_id).map((m) => (
                  <option key={m.id} value={m.id}>{m.nombre_usuario}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t('importe')}</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={liquidacion.importe}
                onChange={(e) => setLiquidacion({ ...liquidacion, importe: e.target.value })}
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t('nota_opcional')}</label>
              <input
                type="text"
                value={liquidacion.nota}
                onChange={(e) => setLiquidacion({ ...liquidacion, nota: e.target.value })}
                className="input-field"
              />
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">{t('guardar')}</button>
              <button type="button" onClick={() => setShowLiquidacion(false)} className="btn-secondary flex-1">{t('cancelar')}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
