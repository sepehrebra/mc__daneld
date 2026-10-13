import { useEffect, useState } from 'react'
import Card from '../Card.jsx'
import { api } from '../../api.js'

export default function Notifications() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  const reload = async () => {
    try {
      setItems(await api.notifications())
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { reload() }, [])

  const markRead = async (id) => {
    try {
      await api.markNotificationRead(id)
      await reload()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <Card title="اعلان‌ها">
      <button type="button" onClick={reload} className="mb-3 text-sm text-primary">به‌روزرسانی</button>
      {error && <p className="text-sm text-danger">{error}</p>}
      {!error && items.length === 0 && <p className="text-sm text-muted">اعلانی ندارید.</p>}
      <ul className="space-y-2">
        {items.map((item) => <li key={item.id} className="flex items-center justify-between gap-2 rounded-xl bg-bg p-3">
          <span>{item.operation_title} — {item.remind_at}</span>
          {!item.read_at && <button type="button" onClick={() => markRead(item.id)}
            className="shrink-0 text-sm text-primary">خواندم</button>}
        </li>)}
      </ul>
    </Card>
  )
}
