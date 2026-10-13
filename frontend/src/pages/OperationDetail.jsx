import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Card from '../components/Card.jsx'
import Button from '../components/Button.jsx'
import { api } from '../api.js'

export default function OperationDetail() {
  const { id } = useParams()
  const [operation, setOperation] = useState(null)
  const [reminders, setReminders] = useState([])
  const [remindAt, setRemindAt] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    Promise.all([api.operation(id), api.reminders(id)])
      .then(([item, items]) => {
        if (active) { setOperation(item); setReminders(items) }
      })
      .catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [id])

  const addReminder = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setSaving(true)
    try {
      const date = new Date(remindAt)
      if (Number.isNaN(date.getTime())) throw new Error('زمان یادآوری معتبر نیست.')
      await api.createReminder(id, { remind_at: date.toISOString() })
      setReminders(await api.reminders(id))
      setRemindAt('')
      setMessage('یادآوری ثبت شد.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const changeStatus = async (status) => {
    setError('')
    try {
      const updated = await api.updateOperation(id, { status })
      setOperation(updated)
      setReminders(await api.reminders(id))
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
          {operation.completed_at && <p className="mt-2">زمان تکمیل: {operation.completed_at}</p>}
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
        <Card title="یادآوری‌ها">
          {reminders.length === 0 ? <p className="text-sm text-muted">یادآوری‌ای ثبت نشده است.</p> : (
            <ul className="space-y-2 text-sm">
              {reminders.map((item) => <li key={item.id}>
                {item.remind_at} — {item.status}
              </li>)}
            </ul>
          )}
          {!['completed', 'cancelled'].includes(operation.status) && (
            <form onSubmit={addReminder} className="mt-4 space-y-3">
              <label className="block text-sm font-medium" htmlFor="remind_at">
                زمان یادآوری (بر اساس ساعت دستگاه شما)
              </label>
              <input id="remind_at" type="datetime-local" required value={remindAt}
                onChange={(event) => setRemindAt(event.target.value)}
                className="h-12 w-full rounded-xl border border-line bg-surface px-3" />
              <Button type="submit" disabled={saving}>ثبت یادآوری</Button>
              {message && <p className="text-sm text-primary">{message}</p>}
            </form>
          )}
        </Card>
      </>}
    </main>
  )
}
