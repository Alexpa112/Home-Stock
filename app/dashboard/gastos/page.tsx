'use client'

import { useState, useEffect } from 'react'
import { Plus, AlertCircle, Receipt, HandCoins, Download, Repeat, Pause, Play, Trash2 } from 'lucide-react'
import { Modal } from '@/components/dashboard/Modal'
import { HojaCompleta } from '@/components/dashboard/HojaCompleta'
import { MenuAcciones } from '@/components/dashboard/MenuAcciones'
import { BarraHorizontal } from '@/components/dashboard/BarraHorizontal'
import { GraficoColumnas } from '@/components/dashboard/GraficoColumnas'
import { SegmentedControl } from '@/components/dashboard/SegmentedControl'
import { ListaGastos } from '@/components/dashboard/gastos/ListaGastos'
import { GastosVacio } from '@/components/dashboard/gastos/GastosVacio'
import { GastoDetalle } from '@/components/dashboard/gastos/GastoDetalle'
import { BalanceHero } from '@/components/dashboard/gastos/BalanceHero'
import { BalancesPanel } from '@/components/dashboard/gastos/BalancesPanel'
import { HistorialLiquidaciones } from '@/components/dashboard/gastos/HistorialLiquidaciones'
import { FormularioGasto, EstadoFormularioGasto } from '@/components/dashboard/gastos/FormularioGasto'
import { gastos as gastosApi, hogares as hogaresApi, categoriasGasto as categoriasGastoApi } from '@/lib/api'
import { useHogar } from '@/contexts/HogarContext'
import { useAuth } from '@/hooks/useAuth'
import { useTranslation } from '@/contexts/TranslationContext'
import { getCached, setCached } from '@/lib/dataCache'
import { usePollingRefresh } from '@/lib/usePollingRefresh'
import { formatImporte } from '@/lib/format'
import { SkeletonCards } from '@/components/dashboard/SkeletonCards'
import {
  totalesPorCategoria,
  evolucionMensual,
  balancePorPersona,
  totalMes,
  variacionMensual,
  parteDeUsuario,
} from '@/lib/gastosStats'

const CACHE_KEY_GASTOS = 'gastos:lista'
const CACHE_KEY_SALDO = 'gastos:saldo'
const CACHE_KEY_SUGERENCIAS = 'gastos:sugerencias'
const CACHE_KEY_LIQUIDACIONES = 'gastos:liquidaciones'
const CACHE_KEY_RECURRENTES = 'gastos:recurrentes'
const CACHE_KEY_CATEGORIAS_GASTO = 'gastos:categorias'
const ID_FORMULARIO_GASTO = 'formulario-gasto'
const SIN_CATEGORIA = '__sin_categoria__'

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
type Vista = 'gastos' | 'balances' | 'resumen'

const fechaHoy = () => new Date().toISOString().slice(0, 10)

const FORM_VACIO = (participantesPorDefecto: number[] = []): EstadoFormularioGasto => ({
  descripcion: '',
  importe_total: '',
  categoria: null,
  fecha: fechaHoy(),
  usuario_pagador_id: null,
  seleccionados: new Set(participantesPorDefecto),
  importesPorMiembro: {},
  porcentajesPorMiembro: {},
  partesPorMiembro: {},
  modoReparto: 'igual',
})

export default function GastosPage() {
  const { t, idioma } = useTranslation()
  const { hogarActivoId, propios, compartidos, refrescar: refrescarHogares } = useHogar()
  const { user } = useAuth()
  const usuarioId = user?.usuario_id ?? null

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
  const [vista, setVista] = useState<Vista>('gastos')
  const [detalleGasto, setDetalleGasto] = useState<Gasto | null>(null)

  const [resumenMes, setResumenMes] = useState<{ gasto_mes: number; presupuesto_mensual: number | null; porcentaje: number | null } | null>(null)
  const [editandoPresupuesto, setEditandoPresupuesto] = useState(false)
  const [presupuestoInput, setPresupuestoInput] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<EstadoFormularioGasto>(FORM_VACIO())
  const [modalEdicionId, setModalEdicionId] = useState<number | null>(null)

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

  const [showLiquidacion, setShowLiquidacion] = useState(false)
  const [liquidacion, setLiquidacion] = useState({ usuario_origen_id: null as number | null, usuario_destino_id: null as number | null, importe: '', nota: '' })
  const [confirmandoLiquidacionId, setConfirmandoLiquidacionId] = useState<number | null>(null)

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
    if (vista !== 'resumen' || !hogarActivoId) return
    gastosApi.resumenMes().then((data: any) => setResumenMes(data)).catch(() => {})
  }, [vista, hogarActivoId, gastos])

  const handleGuardarPresupuesto = async () => {
    if (!hogarActivoId) return
    const valor = presupuestoInput.trim() === '' ? null : parseFloat(presupuestoInput)
    try {
      await hogaresApi.actualizar(hogarActivoId, { presupuesto_mensual: valor })
      await refrescarHogares()
      const datos: any = await gastosApi.resumenMes()
      setResumenMes(datos)
      setEditandoPresupuesto(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_guardar_presupuesto'))
    }
  }

  useEffect(() => {
    categoriasGastoApi.listar().then((data: any) => {
      const arr = Array.isArray(data) ? data : []
      setCategoriasGasto(arr)
      setCached(CACHE_KEY_CATEGORIAS_GASTO, arr)
    }).catch(() => {})
  }, [])

  usePollingRefresh(
    () => cargarDatos(),
    () => showForm || modalEdicionId !== null || showLiquidacion || showRecurrenteForm || detalleGasto !== null
  )

  const getCategoriaGastoIcon = (nombre: string | null | undefined) => {
    if (!nombre) return null
    return categoriasGasto.find((c) => c.nombre === nombre)?.icono || null
  }

  const aplicarModoReparto = (siguiente: EstadoFormularioGasto): EstadoFormularioGasto => {
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
    setForm(FORM_VACIO(miembros.map((m) => m.id)))
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
      fecha: (gasto.fecha || fechaHoy()).slice(0, 10),
      usuario_pagador_id: gasto.usuario_pagador_id,
      seleccionados,
      importesPorMiembro,
      porcentajesPorMiembro: {},
      partesPorMiembro: {},
      modoReparto: 'personalizado',
    })
    setDetalleGasto(null)
    setModalEdicionId(gasto.id)
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
    if (!form.usuario_pagador_id) {
      setError(t('err_seleccionar_pagador') || 'Selecciona quién pagó')
      return
    }
    if (form.seleccionados.size === 0) {
      setError(t('err_sin_participantes') || 'Debe haber al menos un participante')
      return
    }

    const datos = {
      descripcion: form.descripcion.trim(),
      importe_total: parseFloat(form.importe_total) || 0,
      categoria: form.categoria,
      fecha: form.fecha,
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
    try {
      setError('')
      await gastosApi.eliminar(id)
      setDetalleGasto(null)
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_articulo'))
    }
  }

  const handleEliminarLiquidacion = async (id: number) => {
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

  const abrirLiquidacionManual = () => {
    setLiquidacion({ usuario_origen_id: null, usuario_destino_id: null, importe: '', nota: '' })
    setShowLiquidacion(true)
  }

  const abrirLiquidacionPrellenada = (s: SugerenciaPago) => {
    setLiquidacion({
      usuario_origen_id: s.usuario_origen_id,
      usuario_destino_id: s.usuario_destino_id,
      importe: s.importe.toFixed(2),
      nota: '',
    })
    setShowLiquidacion(true)
  }

  const handlePagarSugerencia = async (s: SugerenciaPago) => {
    try {
      setError('')
      await gastosApi.registrarLiquidacion({
        usuario_origen_id: s.usuario_origen_id,
        usuario_destino_id: s.usuario_destino_id,
        importe: s.importe,
      })
      await cargarDatos()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_actualizar'))
    }
  }

  const cerrarFormulario = () => {
    setShowForm(false)
    setModalEdicionId(null)
  }

  const gastoEnEdicion = modalEdicionId !== null ? gastos.find((g) => g.id === modalEdicionId) : null

  const sugerenciasPropias = sugerencias.filter(
    (s) => s.usuario_origen_id === usuarioId || s.usuario_destino_id === usuarioId
  )

  const ymActual = new Date().toISOString().slice(0, 7)
  const fechaMesAnterior = new Date()
  fechaMesAnterior.setDate(1)
  fechaMesAnterior.setMonth(fechaMesAnterior.getMonth() - 1)
  const ymAnterior = fechaMesAnterior.toISOString().slice(0, 7)

  const totalMesActual = totalMes(gastos, ymActual)
  const variacionMes = variacionMensual(gastos, ymActual, ymAnterior)
  const tuParteMes = gastos
    .filter((g) => (g.fecha || '').slice(0, 7) === ymActual)
    .reduce((acc, g) => acc + parteDeUsuario(g, usuarioId), 0)
  const pctTuParte = totalMesActual > 0 ? Math.round((tuParteMes / totalMesActual) * 100) : null

  return (
    <div className="max-w-4xl mx-auto p-4 lg:p-6 space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold flex items-center gap-2">
            <Receipt className="w-7 h-7" /> {t('nav_gastos')}
          </h1>
        </div>
        <MenuAcciones
          label={t('acciones_gastos')}
          acciones={[
            { icono: <Download className="w-4 h-4" />, etiqueta: t('exportar_csv'), onClick: handleExportarCsv },
            { icono: <HandCoins className="w-4 h-4" />, etiqueta: t('registrar_pago'), onClick: abrirLiquidacionManual },
            { icono: <Repeat className="w-4 h-4" />, etiqueta: t('gasto_recurrente'), onClick: () => setShowRecurrenteForm(true) },
          ]}
        />
      </div>

      <SegmentedControl
        valor={vista}
        onCambiar={setVista}
        opciones={[
          { valor: 'gastos', etiqueta: t('nav_gastos') },
          { valor: 'balances', etiqueta: t('balances') },
          { valor: 'resumen', etiqueta: t('resumen') },
        ]}
      />

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {vista === 'gastos' ? (
        <>
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
              <div className="flex flex-wrap gap-3">
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">{t('desde')}</label>
                  <input
                    type="date"
                    value={filtros.desde}
                    onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })}
                    className="input-field !py-1.5 text-sm w-auto"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">{t('hasta')}</label>
                  <input
                    type="date"
                    value={filtros.hasta}
                    onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })}
                    className="input-field !py-1.5 text-sm w-auto"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">{t('categoria')}</label>
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
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">{t('miembro')}</label>
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
            </div>
          )}

          {loading ? (
            <SkeletonCards />
          ) : gastos.length === 0 ? (
            <GastosVacio
              titulo={t('sin_gastos_titulo')}
              descripcion={t('sin_gastos_descripcion')}
              textoBoton={t('nuevo_gasto')}
              onAnadir={abrirModalNuevo}
            />
          ) : gastosFiltrados.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">{t('sin_resultados_filtro')}</p>
            </div>
          ) : (
            <ListaGastos
              gastos={gastosFiltrados}
              simboloMoneda={simboloMoneda}
              idioma={idioma}
              getCategoriaGastoIcon={getCategoriaGastoIcon}
              onAbrirDetalle={setDetalleGasto}
              labelDetalle={t('ver_detalle_gasto')}
            />
          )}
        </>
      ) : vista === 'balances' ? (
        saldo.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">{t('sin_gastos_aun')}</p>
          </div>
        ) : (
          <div className="space-y-4">
            <BalanceHero
              saldo={saldo}
              sugerenciasPropias={sugerenciasPropias}
              usuarioId={usuarioId}
              simboloMoneda={simboloMoneda}
              t={t}
            />
            <BalancesPanel
              sugerencias={sugerencias}
              simboloMoneda={simboloMoneda}
              onSaldar={abrirLiquidacionPrellenada}
              t={t}
            />
            <HistorialLiquidaciones
              liquidaciones={historialLiquidaciones}
              simboloMoneda={simboloMoneda}
              idioma={idioma}
              onDeshacer={handleEliminarLiquidacion}
              t={t}
            />
          </div>
        )
      ) : gastos.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">{t('sin_datos_estadisticas')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="card space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium">{t('presupuesto_mensual')}</h2>
              {!editandoPresupuesto && (
                <button
                  type="button"
                  onClick={() => {
                    setPresupuestoInput(resumenMes?.presupuesto_mensual != null ? String(resumenMes.presupuesto_mensual) : '')
                    setEditandoPresupuesto(true)
                  }}
                  className="text-xs text-accent hover:underline"
                >
                  {t('editar')}
                </button>
              )}
            </div>
            {editandoPresupuesto ? (
              <div className="flex gap-2">
                <input
                  type="number"
                  inputMode="decimal"
                  value={presupuestoInput}
                  onChange={(e) => setPresupuestoInput(e.target.value)}
                  placeholder="0.00"
                  className="input-field flex-1"
                  autoFocus
                />
                <button type="button" onClick={handleGuardarPresupuesto} className="btn-primary !px-4">{t('guardar')}</button>
                <button type="button" onClick={() => setEditandoPresupuesto(false)} className="btn-secondary !px-4">{t('cancelar')}</button>
              </div>
            ) : resumenMes?.presupuesto_mensual !== null && resumenMes?.presupuesto_mensual !== undefined ? (
              <>
                <div className="flex items-baseline justify-between">
                  <span className="text-lg font-bold tabular-nums">{formatImporte(resumenMes.gasto_mes, simboloMoneda)}</span>
                  <span className="text-xs text-muted-foreground">
                    {t('de_presupuesto')} {formatImporte(resumenMes.presupuesto_mensual, simboloMoneda)}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full ${(resumenMes.porcentaje || 0) >= 100 ? 'bg-red-500' : (resumenMes.porcentaje || 0) >= 80 ? 'bg-amber-500' : 'bg-accent'}`}
                    style={{ width: `${Math.min(100, resumenMes.porcentaje || 0)}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">{resumenMes.porcentaje}% {t('presupuesto_consumido')}</p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{t('sin_presupuesto')}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="card space-y-1">
              <p className="text-xs text-muted-foreground">{t('total_mes')}</p>
              <p className="text-xl lg:text-2xl font-bold tabular-nums">{formatImporte(totalMesActual, simboloMoneda)}</p>
              {variacionMes !== null && (
                <p className={`text-xs font-medium ${variacionMes > 0 ? 'text-red-600 dark:text-red-400' : variacionMes < 0 ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
                  {variacionMes > 0 ? '+' : ''}{variacionMes}% {t('vs_mes_anterior')}
                </p>
              )}
            </div>
            <div className="card space-y-1">
              <p className="text-xs text-muted-foreground">{t('tu_parte')}</p>
              <p className="text-xl lg:text-2xl font-bold tabular-nums">{formatImporte(tuParteMes, simboloMoneda)}</p>
              {pctTuParte !== null && (
                <p className="text-xs text-muted-foreground">{pctTuParte}% {t('del_total')}</p>
              )}
            </div>
          </div>
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

      {(showForm || modalEdicionId !== null) && (
        <HojaCompleta
          titulo={modalEdicionId !== null ? t('editar_gasto') : t('nuevo_gasto')}
          onCerrar={cerrarFormulario}
          cabeceraDerecha={
            <button type="submit" form={ID_FORMULARIO_GASTO} className="text-accent font-semibold text-sm px-1">
              {t('guardar')}
            </button>
          }
        >
          <FormularioGasto
            id={ID_FORMULARIO_GASTO}
            form={form}
            miembros={miembros}
            categoriasGasto={categoriasGasto}
            simboloMoneda={simboloMoneda}
            gastoEnEdicion={gastoEnEdicion ? { id: gastoEnEdicion.id, tiene_recibo: gastoEnEdicion.tiene_recibo } : null}
            reciboUrl={gastosApi.reciboUrl}
            onSubmit={handleGuardar}
            onCambiarDescripcion={(valor) => setForm({ ...form, descripcion: valor })}
            onCambiarImporteTotal={cambiarImporteTotal}
            onCambiarCategoria={(valor) => setForm({ ...form, categoria: valor })}
            onCambiarFecha={(valor) => setForm({ ...form, fecha: valor })}
            onCambiarPagador={(id) => setForm({ ...form, usuario_pagador_id: id })}
            onToggleParticipante={toggleParticipante}
            onCambiarModoReparto={cambiarModoReparto}
            onCambiarPorcentajeParticipante={cambiarPorcentajeParticipante}
            onCambiarPartesParticipante={cambiarPartesParticipante}
            onCambiarImporteParticipante={cambiarImporteParticipante}
            onSubirRecibo={handleSubirRecibo}
            onEliminarRecibo={handleEliminarRecibo}
            t={t}
          />
        </HojaCompleta>
      )}

      {detalleGasto && (
        <GastoDetalle
          gasto={detalleGasto}
          icono={getCategoriaGastoIcon(detalleGasto.categoria)}
          simboloMoneda={simboloMoneda}
          idioma={idioma}
          reciboUrl={gastosApi.reciboUrl(detalleGasto.id)}
          onCerrar={() => setDetalleGasto(null)}
          onEditar={abrirModalEdicion}
          onEliminar={handleEliminar}
          t={t}
        />
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

      <button
        onClick={abrirModalNuevo}
        aria-label={t('nuevo_gasto')}
        className="fixed z-40 right-5 bottom-[calc(var(--mobile-toolbar-h)+1.25rem)] lg:bottom-6 w-14 h-14 rounded-2xl bg-accent text-accent-foreground shadow-lg flex items-center justify-center hover:opacity-90 active:scale-95 transition-all"
      >
        <Plus className="w-6 h-6" />
      </button>
    </div>
  )
}
