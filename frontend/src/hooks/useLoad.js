import { useEffect, useState } from 'react'

// یک تابع async را یک‌بار اجرا می‌کند و { data, loading, error } برمی‌گرداند.
export default function useLoad(fn) {
  const [state, setState] = useState({ data: null, loading: true, error: null })

  useEffect(() => {
    let cancelled = false
    fn()
      .then((data) => !cancelled && setState({ data, loading: false, error: null }))
      .catch((e) => !cancelled && setState({ data: null, loading: false, error: e.message }))
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return state
}
