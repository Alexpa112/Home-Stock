'use client'

import { useState, useEffect } from 'react'
import { CheckCircle2, AlertCircle, Loader, Copy } from 'lucide-react'
import { useTranslation } from '@/contexts/TranslationContext'

interface DiagnosticResult {
  name: string
  status: 'loading' | 'success' | 'error'
  message: string
  details?: string
}

export default function DiagnosticsPage() {
  const { t } = useTranslation()
  const [results, setResults] = useState<DiagnosticResult[]>([])
  const [logs, setLogs] = useState<string[]>([])

  useEffect(() => {
    runDiagnostics()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const addLog = (message: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`])
    console.log(message)
  }

  const runDiagnostics = async () => {
    // Todas las peticiones van por ruta relativa: next.config.mjs reescribe
    // /api/:path* hacia NEXT_PUBLIC_API_URL (Flask) DENTRO del servidor de
    // Next, asi que el navegador solo habla con este mismo origen (sin CORS).
    const checks: DiagnosticResult[] = [
      { name: t('backend_flask_check'), status: 'loading', message: t('comprobando') },
      { name: t('token_csrf_check'), status: 'loading', message: t('comprobando') },
      { name: t('sesion_check'), status: 'loading', message: t('comprobando') },
      { name: t('productos_check'), status: 'loading', message: t('comprobando') },
      { name: t('lista_compra_check'), status: 'loading', message: t('comprobando') },
    ]
    setResults([...checks])
    addLog(t('iniciando_diagnostico'))

    // 1. El backend Flask responde (via el proxy de Next)
    try {
      const r = await fetch('/api/auth/estado', { credentials: 'include' })
      checks[0] = {
        name: t('backend_flask_check'),
        status: r.status < 500 ? 'success' : 'error',
        message: r.status < 500 ? t('backend_accesible') : t('respuesta_inesperada').replace('{status}', String(r.status)),
        details: t('detalle_next_public_url').replace('{valor}', process.env.NEXT_PUBLIC_API_URL || t('por_defecto_localhost')),
      }
      addLog(r.status < 500 ? t('log_backend_accesible') : t('log_backend_respondio').replace('{status}', String(r.status)))
    } catch (err) {
      checks[0] = {
        name: t('backend_flask_check'),
        status: 'error',
        message: t('backend_no_conecta'),
        details: `${err instanceof Error ? err.message : err}\n${t('detalle_asegurate_flask')}`,
      }
      addLog(t('log_error_conexion').replace('{error}', String(err)))
    }
    setResults([...checks])

    // 2. Token CSRF
    try {
      const r = await fetch('/api/csrf-token', { credentials: 'include' })
      const datos = await r.json()
      checks[1] = {
        name: t('token_csrf_check'),
        status: r.ok && datos.csrf_token ? 'success' : 'error',
        message: r.ok && datos.csrf_token ? t('token_obtenido') : t('token_no_obtenido'),
        details: t('detalle_status').replace('{status}', String(r.status)),
      }
      addLog(r.ok ? t('log_csrf_ok') : t('log_csrf_fallido'))
    } catch (err) {
      checks[1] = { name: t('token_csrf_check'), status: 'error', message: t('error_obteniendo_token'), details: String(err) }
      addLog(t('log_error_csrf').replace('{error}', String(err)))
    }
    setResults([...checks])

    // 3. Sesion
    try {
      const r = await fetch('/api/auth/estado', { credentials: 'include' })
      const datos = await r.json()
      checks[2] = {
        name: t('sesion_check'),
        status: 'success',
        message: datos.usuario ? t('sesion_iniciada_como').replace('{usuario}', datos.usuario) : t('sesion_no_iniciada'),
        details: JSON.stringify(datos),
      }
      addLog(t('log_endpoint_estado'))
    } catch (err) {
      checks[2] = { name: t('sesion_check'), status: 'error', message: t('error_consultando_estado'), details: String(err) }
      addLog(t('log_error_sesion').replace('{error}', String(err)))
    }
    setResults([...checks])

    // 4. Productos (requiere sesion; 401 es una respuesta valida, no un fallo de conectividad)
    try {
      const r = await fetch('/api/productos', { credentials: 'include' })
      checks[3] = {
        name: t('productos_check'),
        status: r.status === 401 || r.ok ? 'success' : 'error',
        message: r.status === 401 ? t('requiere_sesion_esperado') : r.ok ? t('respondiendo_correctamente') : t('respuesta_inesperada').replace('{status}', String(r.status)),
        details: t('detalle_status').replace('{status}', String(r.status)),
      }
      addLog(t('log_endpoint_productos'))
    } catch (err) {
      checks[3] = { name: t('productos_check'), status: 'error', message: t('error_conexion_titulo'), details: String(err) }
      addLog(t('log_error_productos').replace('{error}', String(err)))
    }
    setResults([...checks])

    // 5. Lista de la compra
    try {
      const r = await fetch('/api/articulos', { credentials: 'include' })
      checks[4] = {
        name: t('lista_compra_check'),
        status: r.status === 401 || r.ok ? 'success' : 'error',
        message: r.status === 401 ? t('requiere_sesion_esperado') : r.ok ? t('respondiendo_correctamente') : t('respuesta_inesperada').replace('{status}', String(r.status)),
        details: t('detalle_status').replace('{status}', String(r.status)),
      }
      addLog(t('log_endpoint_articulos'))
    } catch (err) {
      checks[4] = { name: t('lista_compra_check'), status: 'error', message: t('error_conexion_titulo'), details: String(err) }
      addLog(t('log_error_articulos').replace('{error}', String(err)))
    }
    setResults([...checks])

    addLog(t('diagnostico_completado'))
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-4">
      <div className="max-w-2xl mx-auto py-8">
        <h1 className="text-3xl font-bold mb-2">{t('diagnostico_integracion_titulo')}</h1>
        <p className="text-muted-foreground mb-6">
          {t('diagnostico_integracion_subtitulo')}
        </p>

        {/* Results */}
        <div className="space-y-4 mb-8">
          {results.map((result, idx) => (
            <div key={idx} className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-start gap-3">
                {result.status === 'loading' && (
                  <Loader className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0 mt-1" />
                )}
                {result.status === 'success' && (
                  <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0 mt-1" />
                )}
                {result.status === 'error' && (
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-1" />
                )}

                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-foreground">{result.name}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{result.message}</p>
                  {result.details && (
                    <pre className="bg-muted p-3 rounded mt-2 text-xs overflow-auto max-h-32">
                      {result.details}
                    </pre>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Logs */}
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">{t('logs_diagnostico')}</h2>
            <button
              onClick={() => copyToClipboard(logs.join('\n'))}
              className="p-2 hover:bg-muted rounded transition-colors"
              title={t('copiar_logs')}
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
          <pre className="bg-muted p-3 rounded text-xs overflow-auto max-h-48 text-muted-foreground">
            {logs.length > 0 ? logs.join('\n') : t('sin_logs_aun')}
          </pre>
        </div>

        {/* Action buttons */}
        <div className="mt-6 flex gap-3">
          <button
            onClick={runDiagnostics}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 transition-colors"
          >
            {t('reintentar_diagnostico')}
          </button>
          <a
            href="/dashboard"
            className="px-4 py-2 bg-muted text-foreground rounded-lg font-medium hover:bg-border transition-colors"
          >
            {t('ir_al_dashboard')}
          </a>
        </div>

        {/* Quick help */}
        <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
            {t('problemas_conectividad_titulo')}
          </h3>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>• {t('ayuda_diagnostico_1')}</li>
            <li>• {t('ayuda_diagnostico_2')}</li>
            <li>• {t('ayuda_diagnostico_3')}</li>
            <li>• {t('ayuda_diagnostico_4')}</li>
          </ul>
        </div>
      </div>
    </main>
  )
}
