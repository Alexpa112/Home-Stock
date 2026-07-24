export function getErrorMessage(error: unknown, fallback = 'Error de conexión') {
  return error instanceof Error ? error.message : fallback
}

export function parseNonNegativeInteger(value: string, fallback = 0) {
  const nextValue = parseInt(value, 10)
  if (Number.isNaN(nextValue)) return fallback
  return Math.max(0, nextValue)
}

export function parsePositiveInteger(value: string, fallback = 1) {
  const nextValue = parseInt(value, 10)
  if (Number.isNaN(nextValue)) return fallback
  return Math.max(1, nextValue)
}
