import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import Card from '../components/Card.jsx'
import { api } from '../api.js'

export default function OperationDetail() {
  const { id } = useParams()
  const { state } = useLocation()
  const plotId = state?.plotId
  const [operation, setOperation] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setError('')
    setOperation(null)
    const controller = new AbortController()
    api.operation(id, plotId, controller.signal)
      .then((item) => { if (!controller.signal.aborted) setOperation(item) })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message) })
    return () => controller.abort()
  }, [id, plotId])

  const changeStatus = async (status) => {
    setError('')
    try {
      const updated = await api.updateOperation(id, { status })
      setOperation(updated)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 space-y-5 px-4 py-6">
      <Link to="/dashboard" className="text-sm text-primary">بازگشت به داشبورد</Link>
      {error && <p className="text-sm text-danger">{error}</p>}
      {!operation && !error && <p>در حال بارگذاری...</p>}
      {operation && <>
        <Card title={operation.title}>
          <p>موعد: {operation.scheduled_date} {operation.scheduled_time ?? ''}</p>
          <p className="mt-2">وضعیت: {operation.status}</p>
          {operation.completed_date && <p className="mt-2">تاریخ تکمیل: {operation.completed_date}</p>}
          {operation.status === 'planned' && <div className="mt-4 flex gap-2">
            <button type="button" onClick={() => changeStatus('in_progress')}
              className="rounded-lg bg-primary-soft px-3 py-2 text-primary">شروع</button>
            <button type="button" onClick={() => changeStatus('completed')}
              className="rounded-lg bg-primary-soft px-3 py-2 text-primary">تکمیل</button>
            <button type="button" onClick={() => changeStatus('cancelled')}
              className="rounded-lg bg-bg px-3 py-2 text-danger">لغو</button>
          </div>}
          {operation.status === 'in_progress' && <div className="mt-4 flex gap-2">
            <button type="button" onClick={() => changeStatus('completed')}
              className="rounded-lg bg-primary-soft px-3 py-2 text-primary">تکمیل</button>
            <button type="button" onClick={() => changeStatus('cancelled')}
              className="rounded-lg bg-bg px-3 py-2 text-danger">لغو</button>
          </div>}
        </Card>
      </>}
    </main>
  )
}
