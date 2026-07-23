import { useState, useEffect } from 'react'

interface UseFetchState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useFetch<T>(
  fetchFn: () => Promise<T>,
  dependencies: any[] = []
): UseFetchState<T> {
  const [state, setState] = useState<UseFetchState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  useEffect(() => {
    let isMounted = true

    const fetch = async () => {
      try {
        setState({ data: null, loading: true, error: null })
        const result = await fetchFn()
        if (isMounted) {
          setState({ data: result, loading: false, error: null })
        }
      } catch (err) {
        if (isMounted) {
          const errorMessage = err instanceof Error ? err.message : 'Error desconocido'
          setState({ data: null, loading: false, error: errorMessage })
          console.error('[useFetch] Error:', errorMessage)
        }
      }
    }

    fetch()

    return () => {
      isMounted = false
    }
  }, dependencies)

  return state
}
