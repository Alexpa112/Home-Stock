'use client'

import { useState, useEffect } from 'react'
import { CheckCircle2, AlertCircle, Loader, Copy } from 'lucide-react'

interface DiagnosticResult {
  name: string
  status: 'loading' | 'success' | 'error'
  message: string
  details?: string
}

export default function DiagnosticsPage() {
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
      { name: 'Backend Flask (/)', status: 'loading', message: 'Comprobando...' },
      { name: 'Token CSRF (/api/csrf-token)', status: 'loading', message: 'Comprobando...' },
      { name: 'Sesión (/api/auth/estado)', status: 'loading', message: 'Comprobando...' },
      { name: 'Productos (/api/productos)', status: 'loading', message: 'Comprobando...' },
      { name: 'Lista de la compra (/api/articulos)', status: 'loading', message: 'Comprobando...' },
    ]
    setResults([...checks])
    addLog('Iniciando diagnóstico...')

    // 1. El backend Flask responde (via el proxy de Next)
    try {
      const r = await fetch('/api/auth/estado', { credentials: 'include' })
      checks[0] = {
        name: 'Backend Flask (/)',
        status: r.status < 500 ? 'success' : 'error',
        message: r.status < 500 ? 'Backend accesible a través del proxy de Next' : `Respuesta inesperada (${r.status})`,
        details: `NEXT_PUBLIC_API_URL: ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000 (por defecto)'}`,
      }
      addLog(r.status < 500 ? '✓ Backend accesible' : `✗ Backend respondió ${r.status}`)
    } catch (err) {
      checks[0] = {
        name: 'Backend Flask (/)',
        status: 'error',
        message: 'No se puede conectar al backend',
        details: `${err instanceof Error ? err.message : err}\nAsegúrate que Flask está corriendo (ver run.py) y que NEXT_PUBLIC_API_URL apunta ahí.`,
      }
      addLog(`✗ Error de conexión: ${err}`)
    }
    setResults([...checks])

    // 2. Token CSRF
    try {
      const r = await fetch('/api/csrf-token', { credentials: 'include' })
      const datos = await r.json()
      checks[1] = {
        name: 'Token CSRF (/api/csrf-token)',
        status: r.ok && datos.csrf_token ? 'success' : 'error',
        message: r.ok && datos.csrf_token ? 'Token obtenido correctamente' : 'No se obtuvo el token',
        details: `Status: ${r.status}`,
      }
      addLog(r.ok ? '✓ CSRF token OK' : '✗ CSRF token fallido')
    } catch (err) {
      checks[1] = { name: 'Token CSRF (/api/csrf-token)', status: 'error', message: 'Error obteniendo el token', details: String(err) }
      addLog(`✗ Error CSRF: ${err}`)
    }
    setResults([...checks])

    // 3. Sesion
    try {
      const r = await fetch('/api/auth/estado', { credentials: 'include' })
      const datos = await r.json()
      checks[2] = {
        name: 'Sesión (/api/auth/estado)',
        status: 'success',
        message: datos.usuario ? `Sesión iniciada como "${datos.usuario}"` : 'Sin sesión iniciada (normal si no has hecho login)',
        details: JSON.stringify(datos),
      }
      addLog('✓ Endpoint de estado respondiendo')
    } catch (err) {
      checks[2] = { name: 'Sesión (/api/auth/estado)', status: 'error', message: 'Error consultando el estado', details: String(err) }
      addLog(`✗ Error de sesión: ${err}`)
    }
    setResults([...checks])

    // 4. Productos (requiere sesion; 401 es una respuesta valida, no un fallo de conectividad)
    try {
      const r = await fetch('/api/productos', { credentials: 'include' })
      checks[3] = {
        name: 'Productos (/api/productos)',
        status: r.status === 401 || r.ok ? 'success' : 'error',
        message: r.status === 401 ? 'Requiere sesión (esperado sin login)' : r.ok ? 'Respondiendo correctamente' : `Respuesta inesperada (${r.status})`,
        details: `Status: ${r.status}`,
      }
      addLog('✓ Endpoint de productos respondiendo')
    } catch (err) {
      checks[3] = { name: 'Productos (/api/productos)', status: 'error', message: 'Error de conexión', details: String(err) }
      addLog(`✗ Error productos: ${err}`)
    }
    setResults([...checks])

    // 5. Lista de la compra
    try {
      const r = await fetch('/api/articulos', { credentials: 'include' })
      checks[4] = {
        name: 'Lista de la compra (/api/articulos)',
        status: r.status === 401 || r.ok ? 'success' : 'error',
        message: r.status === 401 ? 'Requiere sesión (esperado sin login)' : r.ok ? 'Respondiendo correctamente' : `Respuesta inesperada (${r.status})`,
        details: `Status: ${r.status}`,
      }
      addLog('✓ Endpoint de artículos respondiendo')
    } catch (err) {
      checks[4] = { name: 'Lista de la compra (/api/articulos)', status: 'error', message: 'Error de conexión', details: String(err) }
      addLog(`✗ Error artículos: ${err}`)
    }
    setResults([...checks])

    addLog('Diagnóstico completado')
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <main className="min-h-screen bg-background text-foreground p-4">
      <div className="max-w-2xl mx-auto py-8">
        <h1 className="text-3xl font-bold mb-2">Diagnóstico de Integración</h1>
        <p className="text-muted-foreground mb-6">
          Verifica la conectividad entre el frontend y el backend
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
            <h2 className="font-semibold">Logs de Diagnóstico</h2>
            <button
              onClick={() => copyToClipboard(logs.join('\n'))}
              className="p-2 hover:bg-muted rounded transition-colors"
              title="Copiar logs"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
          <pre className="bg-muted p-3 rounded text-xs overflow-auto max-h-48 text-muted-foreground">
            {logs.length > 0 ? logs.join('\n') : 'Sin logs aún...'}
          </pre>
        </div>

        {/* Action buttons */}
        <div className="mt-6 flex gap-3">
          <button
            onClick={runDiagnostics}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-600 transition-colors"
          >
            Reintentar Diagnóstico
          </button>
          <a
            href="/dashboard"
            className="px-4 py-2 bg-muted text-foreground rounded-lg font-medium hover:bg-border transition-colors"
          >
            Ir al Dashboard
          </a>
        </div>

        {/* Quick help */}
        <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
            ¿Problemas de conectividad?
          </h3>
          <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
            <li>• Asegúrate que el backend Flask está corriendo (ver run.py)</li>
            <li>• Verifica la variable de entorno NEXT_PUBLIC_API_URL en .env.local</li>
            <li>• Las peticiones van por el proxy de Next (next.config.mjs rewrites), no directas al navegador</li>
            <li>• Consulta el archivo SETUP.md para más información</li>
          </ul>
        </div>
      </div>
    </main>
  )
}
