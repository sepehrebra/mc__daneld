import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import Card from '../components/Card.jsx'
import { api } from '../api.js'

export default function OperationsPage() {
  const { search } = useLocation()
  const [operations, setOperations] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(search)
    let active = true
    const farmId = params.get('farm')
    const plotId = params.get('plot')
    Promise.all([
      api.operations({ plotId, dateFrom: params.get('from'), dateTo: params.get('to') }),
      farmId && !plotId ? api.farms() : Promise.resolve(null),
    ]).then(([items, farms]) => {
      if (!active) return
      const farm = farms?.find((item) => item.id === farmId)
      const plotIds = farms ? new Set((farm?.plots ?? []).map((plot) => plot.id)) : null
      setOperations(plotIds ? items.filter((item) => plotIds.has(item.plot_id)) : items)
    })
      .catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [search])

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 space-y-5 px-4 py-6">
      <Link to="/dashboard" className="text-sm text-primary">بازگشت به داشبورد</Link>
      <Card title="عملیات">
        {error && <p className="text-sm text-danger">{error}</p>}
        {!error && operations.length === 0 && <p className="text-sm text-muted">عملیاتی پیدا نشد.</p>}
        <ul className="space-y-3">
          {operations.map((operation) => <li key={operation.id}>
            <Link to={`/operations/${operation.id}`} className="text-primary">
              {operation.title} — {operation.scheduled_date} — {operation.status}
            </Link>
          </li>)}
        </ul>
      </Card>
    </main>
  )
}
