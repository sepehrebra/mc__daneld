import { Link } from 'react-router-dom'
import Card from '../Card.jsx'
import { formatFa } from '../../utils/date.js'

export default function UpcomingTasks({ data, loading, error }) {
  const tasks = (data ?? []).slice(0, 3)

  return (
    <Card title="کارهای پیش رو">
      {loading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => <div key={i} className="h-12 animate-pulse rounded-xl bg-primary-soft" />)}
        </div>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      {!loading && !error && tasks.length === 0 && (
        <p className="text-sm text-muted">کاری برای روزهای آینده ثبت نشده.</p>
      )}

      <ul className="space-y-2">
        {tasks.map((t) => (
          <li key={t.id} className="flex items-center justify-between gap-3 rounded-xl bg-bg px-3 py-3">
            <span className="font-medium">{t.title}</span>
            <span className="shrink-0 rounded-lg bg-wheat/25 px-2.5 py-1 text-sm text-soil">
              {formatFa(t.date)}
            </span>
          </li>
        ))}
      </ul>

      <Link to="/calendar" className="mt-4 inline-block text-sm font-medium text-primary">
        مشاهده‌ی تقویم کشاورزی
      </Link>
    </Card>
  )
}
