// Pagina estatica de respaldo (P-02): el service worker la sirve cuando una
// navegacion falla por falta de red Y esa URL no tenia nada en cache
// todavia (primera visita sin conexion). Sin fetch de datos, sin cliente:
// tiene que poder renderizarse sin red ni backend disponible.
export default function OfflinePage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background text-foreground p-4">
      <div className="max-w-sm text-center space-y-3">
        <div className="text-5xl mb-2">📡</div>
        <h1 className="text-xl font-semibold">Sin conexión</h1>
        <p className="text-sm text-muted-foreground">
          No se pudo cargar esta página porque no hay conexión a internet y
          todavía no la habías visitado antes. Conéctate y vuelve a intentarlo.
        </p>
      </div>
    </main>
  )
}
