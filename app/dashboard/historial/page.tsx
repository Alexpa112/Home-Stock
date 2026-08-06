'use client'

import { useEffect, useState } from 'react'
import { TrendingDown, BookOpen, Trash2, Pencil, LineChart } from 'lucide-react'
import { consumo as consumoApi, historial as historialApi, articulosPersonalizados as articulosPersonalizadosApi } from '@/lib/api'
import { useTranslation } from '@/contexts/TranslationContext'
import { IconRenderer } from '@/components/dashboard/IconRenderer'
import { IconPicker } from '@/components/dashboard/IconPicker'
import { GraficoColumnas } from '@/components/dashboard/GraficoColumnas'

interface ProductoConsumo {
  nombre: string
  icono: string | null
  consumo: number
}

interface ArticuloCatalogo {
  nombre: string
  icono: string | null
  categoria: string | null
  unidad: string
  cantidad_defecto: number | null
}

interface ArticuloPersonalizado {
  id: number
  nombre: string
  icono: string | null
  categoria: string | null
  unidad: string
  dias_aviso: number
}

const RANGOS = [7, 30, 90]

export default function HistorialPage() {
  const { t } = useTranslation()
  const [dias, setDias] = useState(30)
  const [porProducto, setPorProducto] = useState<ProductoConsumo[]>([])
  const [porDia, setPorDia] = useState<{ dia: string; consumo: number }[]>([])
  const [catalogo, setCatalogo] = useState<ArticuloCatalogo[]>([])
  const [personalizados, setPersonalizados] = useState<ArticuloPersonalizado[]>([])
  const [eliminandoId, setEliminandoId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [diasAvisoEdit, setDiasAvisoEdit] = useState<number | ''>(30)
  const [iconoEdit, setIconoEdit] = useState<string | undefined>(undefined)
  const [mostrarIconPickerId, setMostrarIconPickerId] = useState<number | null>(null)
  const [guardandoId, setGuardandoId] = useState<number | null>(null)

  useEffect(() => {
    cargarConsumo(dias)
    historialApi
      .listar()
      .then((data: any) => setCatalogo(Array.isArray(data) ? data : []))
      .catch(() => {})
    articulosPersonalizadosApi
      .listar()
      .then((data: any) => setPersonalizados(Array.isArray(data) ? data : []))
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const abrirEdicion = (a: ArticuloPersonalizado) => {
    setEditandoId(a.id)
    setDiasAvisoEdit(a.dias_aviso ?? 30)
    setIconoEdit(a.icono ?? undefined)
  }

  const guardarDiasAviso = async (id: number) => {
    setGuardandoId(id)
    setError('')
    try {
      const actualizado: any = await articulosPersonalizadosApi.actualizar(id, {
        dias_aviso: diasAvisoEdit === '' ? null : diasAvisoEdit,
        icono: iconoEdit,
      })
      setPersonalizados((prev) => prev.map((a) => (a.id === id ? { ...a, dias_aviso: actualizado.dias_aviso, icono: actualizado.icono } : a)))
      setEditandoId(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_editar_articulo'))
    } finally {
      setGuardandoId(null)
    }
  }

  const eliminarPersonalizado = async (id: number) => {
    if (!window.confirm(t('eliminar_pregunta'))) return
    setEliminandoId(id)
    setError('')
    try {
      await articulosPersonalizadosApi.eliminar(id)
      setPersonalizados((prev) => prev.filter((a) => a.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('err_eliminar_articulo_personalizado'))
    } finally {
      setEliminandoId(null)
    }
  }

  const cargarConsumo = async (d: number) => {
    try {
      setLoading(true)
      setError('')
      const data: any = await consumoApi.resumen(d)
      setPorProducto(data.por_producto || [])
      setPorDia(data.dias || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de conexión')
    } finally {
      setLoading(false)
    }
  }

  const cambiarRango = (d: number) => {
    setDias(d)
    cargarConsumo(d)
  }

  const maxConsumo = Math.max(1, ...porProducto.map((p) => p.consumo))

  return (
    <div className="max-w-2xl mx-auto p-4 lg:p-6 space-y-6">
      <div>
        <h1 className="text-2xl lg:text-3xl font-bold">{t('historial')}</h1>
        <p className="text-muted-foreground mt-1">{t('subtitulo_historial')}</p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-200 rounded-lg text-sm">{error}</div>
      )}

      <div className="card space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-accent" /> {t('mas_consumido')}
          </h2>
          <div className="flex gap-1 bg-muted p-1 rounded-xl">
            {RANGOS.map((r) => (
              <button
                key={r}
                onClick={() => cambiarRango(r)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all min-h-[36px] ${
                  dias === r
                    ? 'bg-card text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t('n_dias').replace('{n}', String(r))}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">{t('cargando')}</p>
        ) : porProducto.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {t('sin_consumo_registrado')}
          </p>
        ) : (
          <div className="space-y-3">
            {porProducto.map((p, i) => (
              <div key={i} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm gap-2">
                  <span className="font-medium truncate flex items-center gap-1.5">
                    {p.icono && <IconRenderer name={p.icono} className="w-4 h-4 shrink-0" />}
                    {p.nombre}
                  </span>
                  <span className="text-muted-foreground tabular-nums shrink-0 font-medium">{p.consumo}</span>
                </div>
                <div className="h-2.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500"
                    style={{ width: `${Math.max(4, (p.consumo / maxConsumo) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {porDia.length > 0 && (
        <div className="card space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <LineChart className="w-5 h-5 text-accent" /> {t('evolucion_consumo')}
          </h2>
          <GraficoColumnas
            datos={porDia.map((d) => ({ etiqueta: d.dia.slice(5), valor: d.consumo }))}
          />
        </div>
      )}

      <div className="card space-y-3">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-accent" /> {t('catalogo_aprendido')} ({catalogo.length})
        </h2>
        <p className="text-sm text-muted-foreground">
          {t('descripcion_catalogo_aprendido')}
        </p>
        {catalogo.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-80 overflow-y-auto">
            {catalogo.map((a, i) => (
              <div key={i} className="p-2 rounded-lg bg-muted text-sm truncate" title={a.nombre}>
                {a.nombre}
              </div>
            ))}
          </div>
        )}
      </div>

      {personalizados.length > 0 && (
        <div className="card space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-accent" /> {t('mis_articulos_personalizados')} ({personalizados.length})
          </h2>
          <p className="text-sm text-muted-foreground">
            {t('descripcion_mis_articulos_personalizados')}
          </p>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {personalizados.map((a) => (
              <div key={a.id} className="p-2 rounded-lg bg-muted text-sm space-y-2">
                <div className="flex items-center gap-2">
                  {a.icono && <IconRenderer name={a.icono} className="w-4 h-4 shrink-0" />}
                  <span className="truncate flex-1" title={a.nombre}>{a.nombre}</span>
                  <button
                    type="button"
                    onClick={() => (editandoId === a.id ? setEditandoId(null) : abrirEdicion(a))}
                    aria-label={`${t('editar')} ${a.nombre}`}
                    className="p-1.5 rounded-md text-muted-foreground hover:bg-background disabled:opacity-50 shrink-0"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => eliminarPersonalizado(a.id)}
                    disabled={eliminandoId === a.id}
                    aria-label={`${t('eliminar')} ${a.nombre}`}
                    className="p-1.5 rounded-md text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50 shrink-0"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                {editandoId === a.id && (
                  <div className="flex flex-col gap-2 pl-6">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setMostrarIconPickerId(a.id)}
                      className="w-8 h-8 shrink-0 rounded-lg bg-card border border-border flex items-center justify-center"
                      aria-label={t('cambiar_icono')}
                    >
                      {iconoEdit ? (
                        <IconRenderer name={iconoEdit} className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <Pencil className="w-4 h-4 text-muted-foreground" />
                      )}
                    </button>
                    <span className="text-xs text-muted-foreground">{t('cambiar_icono')}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <label htmlFor={`dias-aviso-${a.id}`} className="text-xs text-muted-foreground flex-1">
                      {t('dias_sin_actualizar_para_avisar')}
                    </label>
                    <input
                      id={`dias-aviso-${a.id}`}
                      type="number"
                      min={1}
                      max={365}
                      value={diasAvisoEdit}
                      onChange={(e) => setDiasAvisoEdit(e.target.value === '' ? '' : parseInt(e.target.value))}
                      className="input-field w-20 py-1"
                      inputMode="numeric"
                    />
                    <button
                      type="button"
                      onClick={() => guardarDiasAviso(a.id)}
                      disabled={guardandoId === a.id}
                      className="btn-primary btn-sm disabled:opacity-50"
                    >
                      {t('guardar')}
                    </button>
                  </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {mostrarIconPickerId !== null && (
        <IconPicker
          valorActual={iconoEdit}
          onSeleccionar={(icono) => {
            setIconoEdit(icono)
            setMostrarIconPickerId(null)
          }}
          onCerrar={() => setMostrarIconPickerId(null)}
        />
      )}
    </div>
  )
}
