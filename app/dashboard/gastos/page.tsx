'use client'

import { useState, useEffect } from 'react'
import { Plus, Trash2, Pencil, AlertCircle, Receipt, HandCoins, Download, Tags, X, Paperclip, Repeat, Pause, Play } from 'lucide-react'
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
const CACHE_KEY_LIQUIDACIONES = 'gastos:liquidaciones'
const CACHE_KEY_RECURRENTES = 'gastos:recurrentes'
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
  tiene_recibo: boolean
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

interface LiquidacionItem {
  id: number
  usuario_origen_id: number
  origen_nombre: string
  usuario_destino_id: number
  destino_nombre: string
  importe: number
  fecha: string
  nota: string | null
}

type FrecuenciaRecurrente = 'semanal' | 'mensual' | 'anual'

interface GastoRecurrente {
  id: number
  descripcion: string
  importe_total: number
  categoria?: string | null
  usuario_pagador_id: number
  frecuencia: FrecuenciaRecurrente
  proxima_fecha: string
  fecha_fin: string | null
  activo: boolean
  participantes: Participante[]
}

interface Miembro {
  id: number
  nombre_usuario: string
}

type ModoReparto = 'igual' | 'porcentaje' | 'partes' | 'personalizado'

interface FormularioGasto {
  descripcion: string
  importe_total: string
  categoria: string | null
  usuario_pagador_id: number | null
  seleccionados: Set<number>
  importesPorMiembro: Record<number, string>
  porcentajesPorMiembro: Record<number, string>
  partesPorMiembro: Record<number, string>
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
  partesPorMiembro: {},
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
  const [historialLiquidaciones, setHistorialLiquidaciones] = useState<LiquidacionItem[]>(
    () => getCached<LiquidacionItem[]>(CACHE_KEY_LIQUIDACIONES) || []
  )
  const [confirmandoLiquidacionId, setConfirmandoLiquidacionId] = useState<number | null>(null)
  const [recurrentes, setRecurrentes] = useState<GastoRecurrente[]>(
    () => getCached<GastoRecurrente[]>(CACHE_KEY_RECURRENTES) || []
  )
  const [confirmandoRecurrenteId, setConfirmandoRecurrenteId] = useState<number | null>(null)
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

  const SIN_CATEGORIA = '__sin_categoria__'
  const [filtros, setFiltros] = useState({ desde: '', hasta: '', categoria: '', miembroId: '' })
  const hayFiltrosActivos = Boolean(filtros.desde || filtros.hasta || filtros.categoria || filtros.miembroId)
  const limpiarFiltros = () => setFiltros({ desde: '', hasta: '', categoria: '', miembroId: '' })

  const gastosFiltrados = gastos.filter((g) => {
    const fechaGasto = g.fecha.slice(0, 10)
    if (filtros.desde && fechaGasto < filtros.desde) return false
    if (filtros.hasta && fechaGasto > filtros.hasta) return false
    if (filtros.categoria) {
      const categoriaGasto = g.categoria || SIN_CATEGORIA
      if (categoriaGasto !== filtros.categoria) return false
    }
    if (filtros.miembroId) {
      const miembroId = Number(filtros.miembroId)
      const involucrado = g.usuario_pagador_id === miembroId || g.participantes.some((p) => p.usuario_id === miembroId)
      if (!involucrado) return false
    }
    return true
  })

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

  const FORM_RECURRENTE_VACIO = {
    descripcion: '',
    importe_total: '',
    categoria: null as string | null,
    usuario_pagador_id: null as number | null,
    seleccionados: new Set<number>(),
    frecuencia: 'mensual' as FrecuenciaRecurrente,
    fecha_inicio: '',
    fecha_fin: '',
  }
  const [showRecurrenteForm, setShowRecurrenteForm] = useState(false)
  const [formRecurrente, setFormRecurrente] = useState(FORM_RECURRENTE_VACIO)

  const toggleParticipanteRecurrente = (id: number) => {
    setFormRecurrente((prev) => {
      const seleccionados = new Set(prev.seleccionados)
      if (seleccionados.has(id)) seleccionados.delete(id)
      else seleccionados.add(id)
      return { ...prev, seleccionados }
    })
  }

  const handleCrearRecurrente = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formRecurrente.usuario_pagador_id || formRecurrente.seleccionados.size === 0) return

    const importeTotal = parseFloat(formRecurrente.importe_total) || 0
    const ids = Array.from(formRecurrente.seleccionados)
    const porCabeza = Math.round((importeTotal / ids.length) * 100) / 100
    const participantes = ids.map((id, idx) => ({
      usuario_id: id,
      importe: idx === ids.length - 1
        ? Math.round((importeTotal - porCabeza * (ids.length - 1)) * 100) / 100
        : porCabeza,
    }))

    try {
      setError('')
      await gastosApi.crearRecurrente({
        descripcion: formRecurrente.descripcion,
        importe_total: importeTotal,
        usuario_pagador_id: formRecurrente.usuario_pagador_id,
        categoria: formRecurrente.categoria,
        frecuencia: formRecurrente.frecuencia,
        fecha_inicio: formRecurrente.fecha_inicio,
        fecha_fin: formRecurrente.fecha_fin || undefined,
        participantes,
      })
      setShowRecurrenteForm(false)
      setFormRecurrente(FORM_RECURRENTE_VACIO)
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_actualizar'))
    }
  }

  const handleTogglePausaRecurrente = async (r: GastoRecurrente) => {
    try {
      setError('')
      await gastosApi.pausarRecurrente(r.id, !r.activo)
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_actualizar'))
    }
  }

  const handleEliminarRecurrente = async (id: number) => {
    if (confirmandoRecurrenteId !== id) {
      setConfirmandoRecurrenteId(id)
      return
    }
    setConfirmandoRecurrenteId(null)
    try {
      setError('')
      await gastosApi.eliminarRecurrente(id)
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_articulo'))
    }
  }

  const cargarDatos = async () => {
    try {
      setError('')
      const [gastosData, saldoData, sugerenciasData, liquidacionesData, recurrentesData] = await Promise.all([
        gastosApi.listar(), gastosApi.saldo(), gastosApi.simplificar(), gastosApi.listarLiquidaciones(),
        gastosApi.listarRecurrentes(),
      ])
      const gastosArr = Array.isArray(gastosData) ? gastosData : []
      const saldoArr = Array.isArray(saldoData) ? saldoData : []
      const sugerenciasArr = Array.isArray(sugerenciasData) ? sugerenciasData : []
      const liquidacionesArr = Array.isArray(liquidacionesData) ? liquidacionesData : []
      const recurrentesArr = Array.isArray(recurrentesData) ? recurrentesData : []
      setGastos(gastosArr)
      setSaldo(saldoArr)
      setSugerencias(sugerenciasArr)
      setHistorialLiquidaciones(liquidacionesArr)
      setRecurrentes(recurrentesArr)
      setCached(CACHE_KEY_GASTOS, gastosArr)
      setCached(CACHE_KEY_SALDO, saldoArr)
      setCached(CACHE_KEY_SUGERENCIAS, sugerenciasArr)
      setCached(CACHE_KEY_LIQUIDACIONES, liquidacionesArr)
      setCached(CACHE_KEY_RECURRENTES, recurrentesArr)
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
    () => showForm || modalEdicionId !== null || showLiquidacion || gestionandoCategoriasGasto || showRecurrenteForm
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

    if (siguiente.modoReparto === 'partes') {
      const partes = ids.map((id) => Math.max(0, parseInt(siguiente.partesPorMiembro[id] || '1', 10) || 0))
      const totalPartes = partes.reduce((acc, p) => acc + p, 0)
      const importesPorMiembro: Record<number, string> = {}
      if (totalPartes === 0) {
        ids.forEach((id) => { importesPorMiembro[id] = '0.00' })
        return { ...siguiente, importesPorMiembro }
      }
      let acumulado = 0
      ids.forEach((id, idx) => {
        if (idx === ids.length - 1) {
          importesPorMiembro[id] = (Math.round((importeTotal - acumulado) * 100) / 100).toFixed(2)
        } else {
          const importe = Math.round(importeTotal * (partes[idx] / totalPartes) * 100) / 100
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

  const cambiarPartesParticipante = (id: number, valor: string) => {
    setForm((prev) => aplicarModoReparto({
      ...prev,
      modoReparto: 'partes',
      partesPorMiembro: { ...prev.partesPorMiembro, [id]: valor },
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
      partesPorMiembro: {},
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

  const handleEliminarLiquidacion = async (id: number) => {
    if (confirmandoLiquidacionId !== id) {
      setConfirmandoLiquidacionId(id)
      return
    }
    setConfirmandoLiquidacionId(null)
    try {
      setError('')
      await gastosApi.eliminarLiquidacion(id)
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_articulo'))
    }
  }

  const handleSubirRecibo = async (gastoId: number, file: File) => {
    try {
      setError('')
      await gastosApi.subirRecibo(gastoId, file)
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_actualizar'))
    }
  }

  const handleEliminarRecibo = async (gastoId: number) => {
    try {
      setError('')
      await gastosApi.eliminarRecibo(gastoId)
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

  const renderFormularioGasto = () => {
    const gastoEnEdicion = modalEdicionId !== null ? gastos.find((g) => g.id === modalEdicionId) : null
    return (
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
            {(['igual', 'porcentaje', 'partes', 'personalizado'] as const).map((modo) => (
              <button
                key={modo}
                type="button"
                onClick={() => cambiarModoReparto(modo)}
                className={`px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
                  form.modoReparto === modo ? 'bg-primary text-white' : 'bg-muted text-muted-foreground'
                }`}
              >
                {t(
                  modo === 'igual' ? 'dividir_partes_iguales'
                    : modo === 'porcentaje' ? 'dividir_por_porcentaje'
                    : modo === 'partes' ? 'dividir_por_partes'
                    : 'dividir_personalizado'
                )}
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
              ) : form.modoReparto === 'partes' ? (
                <>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    disabled={!form.seleccionados.has(m.id)}
                    value={form.partesPorMiembro[m.id] ?? '1'}
                    onChange={(e) => cambiarPartesParticipante(m.id, e.target.value)}
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

      {gastoEnEdicion && (
        <div>
          <label className="block text-sm font-medium mb-2">{t('recibo')}</label>
          {gastoEnEdicion.tiene_recibo ? (
            <div className="flex items-center gap-3">
              <a
                href={gastosApi.reciboUrl(gastoEnEdicion.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent hover:underline flex items-center gap-1"
              >
                <Paperclip className="w-4 h-4" /> {t('ver_recibo')}
              </a>
              <button
                type="button"
                onClick={() => handleEliminarRecibo(gastoEnEdicion.id)}
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
                if (file) handleSubirRecibo(gastoEnEdicion.id, file)
              }}
              className="text-sm"
            />
          )}
        </div>
      )}

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
  }

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
          <button onClick={() => setShowRecurrenteForm(true)} className="btn-secondary flex items-center gap-2 min-h-[44px]">
            <Repeat className="w-5 h-5" />
            <span className="hidden sm:inline">{t('gasto_recurrente')}</span>
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

          {historialLiquidaciones.length > 0 && (
            <div className="card space-y-2">
              <h2 className="text-lg font-semibold">{t('historial_pagos')}</h2>
              <div className="space-y-2">
                {historialLiquidaciones.map((l) => (
                  <div key={l.id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate">
                      {l.origen_nombre} → {l.destino_nombre}: {formatImporte(l.importe, simboloMoneda)}
                      {l.nota ? ` (${l.nota})` : ''}
                    </span>
                    {confirmandoLiquidacionId === l.id ? (
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <button onClick={() => handleEliminarLiquidacion(l.id)} className="px-2 h-8 text-xs font-semibold text-white bg-red-500 rounded-xl">{t('si')}</button>
                        <button onClick={() => setConfirmandoLiquidacionId(null)} className="px-2 h-8 text-xs font-semibold text-foreground bg-muted rounded-xl">{t('no')}</button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleEliminarLiquidacion(l.id)}
                        className="w-8 h-8 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors flex-shrink-0"
                        aria-label={t('eliminar')}
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {recurrentes.length > 0 && (
            <div className="card space-y-2">
              <h2 className="text-lg font-semibold">{t('gastos_recurrentes')}</h2>
              <div className="space-y-2">
                {recurrentes.map((r) => (
                  <div key={r.id} className="flex items-center justify-between gap-2 text-sm">
                    <span className={`truncate ${r.activo ? '' : 'text-muted-foreground line-through'}`}>
                      {r.descripcion} · {formatImporte(r.importe_total, simboloMoneda)} · {t(
                        r.frecuencia === 'semanal' ? 'frecuencia_semanal'
                          : r.frecuencia === 'anual' ? 'frecuencia_anual'
                          : 'frecuencia_mensual'
                      )}
                    </span>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={() => handleTogglePausaRecurrente(r)}
                        className="w-8 h-8 flex items-center justify-center hover:bg-muted rounded-xl transition-colors"
                        aria-label={t(r.activo ? 'pausar' : 'reanudar')}
                      >
                        {r.activo ? <Pause className="w-4 h-4 text-muted-foreground" /> : <Play className="w-4 h-4 text-muted-foreground" />}
                      </button>
                      {confirmandoRecurrenteId === r.id ? (
                        <div className="flex items-center gap-1">
                          <button onClick={() => handleEliminarRecurrente(r.id)} className="px-2 h-8 text-xs font-semibold text-white bg-red-500 rounded-xl">{t('si')}</button>
                          <button onClick={() => setConfirmandoRecurrenteId(null)} className="px-2 h-8 text-xs font-semibold text-foreground bg-muted rounded-xl">{t('no')}</button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleEliminarRecurrente(r.id)}
                          className="w-8 h-8 flex items-center justify-center hover:bg-red-50 dark:hover:bg-red-950 rounded-xl transition-colors"
                          aria-label={t('eliminar')}
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!loading && gastos.length > 0 && (
            <div className="card space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">{t('filtros')}</h2>
                {hayFiltrosActivos && (
                  <button onClick={limpiarFiltros} className="text-xs text-primary font-medium">{t('limpiar_filtros')}</button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <input
                  type="date"
                  value={filtros.desde}
                  onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })}
                  className="input-field !py-1.5 text-sm w-auto"
                  aria-label={t('desde')}
                />
                <input
                  type="date"
                  value={filtros.hasta}
                  onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })}
                  className="input-field !py-1.5 text-sm w-auto"
                  aria-label={t('hasta')}
                />
                <select
                  value={filtros.categoria}
                  onChange={(e) => setFiltros({ ...filtros, categoria: e.target.value })}
                  className="input-field !py-1.5 text-sm w-auto"
                >
                  <option value="">{t('todas_las_categorias')}</option>
                  <option value={SIN_CATEGORIA}>{t('sin_categoria')}</option>
                  {categoriasGasto.map((cat) => (
                    <option key={cat.id} value={cat.nombre}>{cat.nombre}</option>
                  ))}
                </select>
                <select
                  value={filtros.miembroId}
                  onChange={(e) => setFiltros({ ...filtros, miembroId: e.target.value })}
                  className="input-field !py-1.5 text-sm w-auto"
                >
                  <option value="">{t('todos_los_miembros')}</option>
                  {miembros.map((m) => (
                    <option key={m.id} value={m.id}>{m.nombre_usuario}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {loading ? (
            <SkeletonCards />
          ) : gastos.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">{t('sin_gastos_aun')}</p>
            </div>
          ) : gastosFiltrados.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">{t('sin_resultados_filtro')}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {gastosFiltrados.map((gasto) => {
                const iconoCategoria = getCategoriaGastoIcon(gasto.categoria)
                return (
                <div key={gasto.id} className="card flex items-center justify-between gap-4">
                  {iconoCategoria && (
                    <IconRenderer name={iconoCategoria} className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate flex items-center gap-1.5">
                      {gasto.descripcion}
                      {gasto.tiene_recibo && (
                        <a
                          href={gastosApi.reciboUrl(gasto.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          aria-label={t('ver_recibo')}
                        >
                          <Paperclip className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                        </a>
                      )}
                    </p>
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

      {showRecurrenteForm && (
        <Modal onCerrar={() => { setShowRecurrenteForm(false); setFormRecurrente(FORM_RECURRENTE_VACIO) }}>
          <form onSubmit={handleCrearRecurrente} className="space-y-4">
            <h2 className="text-lg font-semibold">{t('gasto_recurrente')}</h2>

            <div>
              <label className="block text-sm font-medium mb-2">{t('descripcion')}</label>
              <input
                type="text"
                value={formRecurrente.descripcion}
                onChange={(e) => setFormRecurrente({ ...formRecurrente, descripcion: e.target.value })}
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
                value={formRecurrente.importe_total}
                onChange={(e) => setFormRecurrente({ ...formRecurrente, importe_total: e.target.value })}
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t('pagado_por')}</label>
              <select
                value={formRecurrente.usuario_pagador_id ?? ''}
                onChange={(e) => setFormRecurrente({ ...formRecurrente, usuario_pagador_id: Number(e.target.value) })}
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
              <label className="block text-sm font-medium mb-2">{t('participantes')}</label>
              <div className="space-y-2">
                {miembros.map((m) => (
                  <label key={m.id} className="flex items-center gap-3 text-sm">
                    <input
                      type="checkbox"
                      checked={formRecurrente.seleccionados.has(m.id)}
                      onChange={() => toggleParticipanteRecurrente(m.id)}
                    />
                    {m.nombre_usuario}
                  </label>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t('frecuencia')}</label>
              <select
                value={formRecurrente.frecuencia}
                onChange={(e) => setFormRecurrente({ ...formRecurrente, frecuencia: e.target.value as FrecuenciaRecurrente })}
                className="input-field"
              >
                <option value="semanal">{t('frecuencia_semanal')}</option>
                <option value="mensual">{t('frecuencia_mensual')}</option>
                <option value="anual">{t('frecuencia_anual')}</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t('fecha_inicio')}</label>
              <input
                type="date"
                value={formRecurrente.fecha_inicio}
                onChange={(e) => setFormRecurrente({ ...formRecurrente, fecha_inicio: e.target.value })}
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t('fecha_fin_opcional')}</label>
              <input
                type="date"
                value={formRecurrente.fecha_fin}
                onChange={(e) => setFormRecurrente({ ...formRecurrente, fecha_fin: e.target.value })}
                className="input-field"
              />
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary flex-1">{t('guardar')}</button>
              <button
                type="button"
                onClick={() => { setShowRecurrenteForm(false); setFormRecurrente(FORM_RECURRENTE_VACIO) }}
                className="btn-secondary flex-1"
              >
                {t('cancelar')}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
