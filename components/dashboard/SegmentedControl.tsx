'use client'

interface Opcion<T extends string> {
  valor: T
  etiqueta: string
}

interface SegmentedControlProps<T extends string> {
  opciones: Opcion<T>[]
  valor: T
  onCambiar: (valor: T) => void
}

// Control de 3 posiciones a ancho completo (opción 2A del rediseño de
// gastos, docs/REDISENO_GASTOS.md): reemplaza los botones-píldora sueltos
// por un único grupo con la posición activa resaltada, más fácil de pulsar
// con el pulgar en móvil.
export function SegmentedControl<T extends string>({ opciones, valor, onCambiar }: SegmentedControlProps<T>) {
  return (
    <div className="flex gap-1 p-1 bg-muted rounded-xl" role="tablist">
      {opciones.map((o) => (
        <button
          key={o.valor}
          role="tab"
          aria-selected={valor === o.valor}
          onClick={() => onCambiar(o.valor)}
          className={`flex-1 min-h-[40px] rounded-lg text-sm font-semibold transition-colors ${
            valor === o.valor ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'
          }`}
        >
          {o.etiqueta}
        </button>
      ))}
    </div>
  )
}
