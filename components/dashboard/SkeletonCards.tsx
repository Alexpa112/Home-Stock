'use client'

/** Placeholder con la misma forma que las tarjetas de producto/artículo, para
 * pintar algo con estructura real mientras llegan los datos (en vez de un
 * mensaje de texto o pantalla en blanco). */
export function SkeletonCards({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card animate-pulse space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div className="h-4 bg-muted rounded w-2/3" />
            <div className="h-8 w-8 bg-muted rounded-xl" />
          </div>
          <div className="h-3 bg-muted rounded w-1/3" />
          <div className="pt-3 border-t border-border flex items-center justify-between">
            <div className="h-3 bg-muted rounded w-8" />
            <div className="h-8 bg-muted rounded-xl w-24" />
          </div>
        </div>
      ))}
    </div>
  )
}
