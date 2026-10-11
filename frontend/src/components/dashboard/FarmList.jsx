import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import Card from '../Card.jsx'

export default function FarmList({ data, loading, error }) {
  return (
    <Card title="مزرعه‌های من">
      {loading && <div className="h-10 animate-pulse rounded-xl bg-primary-soft" />}
      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      {!loading && (
        <div className="flex flex-wrap gap-2">
          {(data ?? []).map((f) => (
            <Link
              key={f.id}
              to={`/farms/${f.id}`}
              className="rounded-xl bg-primary-soft px-4 py-2.5 font-medium text-primary hover:bg-primary hover:text-white"
            >
              {f.name}
            </Link>
          ))}

          <Link
            to="/farms/new"
            className="flex items-center gap-1.5 rounded-xl border border-dashed border-primary px-4 py-2.5 font-medium text-primary hover:bg-primary-soft"
          >
            <Plus size={16} />
            افزودن مزرعه
          </Link>
        </div>
      )}
    </Card>
  )
}
