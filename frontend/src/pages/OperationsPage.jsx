import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import Card from '../components/Card.jsx'
import { api } from '../api.js'

export default function OperationsPage() {
  const { pathname, search } = useLocation()
  return <OperationResults key={pathname + search} search={search} recent={pathname === '/operations/recent'} />
}

function OperationResults({ search, recent }) {
  const [operations, setOperations] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(false)
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const limit = recent ? 5 : 20
    const filters = recent
      ? { sort: 'created' }
      : Object.fromEntries(new URLSearchParams(search))
    api.operations({ ...filters, limit, offset }, controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return
        setOperations((previous) => [...previous, ...items])
        setHasMore(!recent && items.length === limit)
      })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [search, recent, offset])

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 space-y-5 px-4 py-6">
      <Link to="/dashboard" className="text-sm text-primary">بازگشت به داشبورد</Link>
      <Card title="عملیات">
        {error && <p className="text-sm text-danger">{error}</p>}
        {!error && !loading && operations.length === 0 && <p className="text-sm text-muted">عملیاتی پیدا نشد.</p>}
        <ul className="space-y-3">
          {operations.map((operation) => <li key={operation.id}>
            <Link to={`/operations/${operation.id}`} state={{ plotId: operation.plot.id }} className="text-primary">
              {operation.title} — {operation.scheduled_date} — {operation.status}
            </Link>
          </li>)}
        </ul>
        {hasMore && !error && <button type="button" disabled={loading} className="mt-4 text-primary"
          onClick={() => { setLoading(true); setOffset((previous) => previous + 20) }}>
          نمایش بیشتر
        </button>}
      </Card>
    </main>
  )
}
