import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Pencil } from 'lucide-react'
import Card from '../components/Card.jsx'
import Stat from '../components/Stat.jsx'
import InfoRows from '../components/InfoRows.jsx'
import SectionTitle from '../components/SectionTitle.jsx'
import OperationCard from '../components/OperationCard.jsx'
import PlotFormModal from '../components/farms/PlotFormModal.jsx'
import useLoad from '../hooks/useLoad.js'
import { api } from '../api.js'
import { formatFa } from '../utils/date.js'
import { daysAgoFa, formatArea } from '../utils/format.js'

const Page = ({ children }) => (
  <main className="mx-auto w-full max-w-2xl flex-1 space-y-5 px-4 py-6">{children}</main>
)

const lastDone = (iso) => (iso ? daysAgoFa(iso) : 'ثبت نشده')

// key={id}: با عوض شدن قطعه، صفحه از نو بارگذاری می‌شود
export default function PlotDetail() {
  const { id } = useParams()
  return <PlotDetailView key={id} id={id} />
}

function SeeAll({ to, children }) {
  return (
    <Link to={to} className="inline-flex items-center gap-1 text-sm font-medium text-primary">
      {children}
      <ChevronLeft size={16} />
    </Link>
  )
}

function PlotDetailView({ id }) {
  const plot = useLoad(() => api.plot(id))
  const [editing, setEditing] = useState(false)
  const p = plot.data

  if (!p) {
    return (
      <Page>
        {plot.loading ? (
          <>
            <div className="mx-auto h-8 w-40 animate-pulse rounded-xl bg-primary-soft" />
            <div className="h-56 animate-pulse rounded-2xl bg-primary-soft" />
            <div className="h-44 animate-pulse rounded-2xl bg-primary-soft" />
          </>
        ) : (
          <>
            <p className="text-sm text-danger">{plot.error}</p>
            <Link to="/farms" className="text-sm font-medium text-primary">بازگشت به مزرعه‌ها</Link>
          </>
        )}
      </Page>
    )
  }

  const season = p.current_season
  const crop = season && (season.variety ? `${season.crop_name} (${season.variety})` : season.crop_name)
  const planted = season
    ? `${formatFa(season.actual_start_date ?? season.start_date)}${season.actual_start_date ? '' : ' (برنامه‌ریزی‌شده)'}`
    : '—'

  // لینک «تمام ...»: صفحه‌ی جست‌وجو با مزرعه و قطعه‌ی همین صفحه
  const search = (extra) => `/operations/search?farm=${p.farm.id}&plot=${p.id}&${extra}`

  const status = [
    ['محصول فعلی', crop ?? 'کشتی ثبت نشده'],
    ['تاریخ کاشت', planted],
    ['آخرین آبیاری', lastDone(p.last_done?.irrigation)],
    ['آخرین کوددهی', lastDone(p.last_done?.fertilizing)],
    ['آخرین سم‌پاشی', lastDone(p.last_done?.spraying)],
  ]

  const info = [
    ['نام قطعه', p.name],
    p.code && ['کد', p.code],
    ['مساحت', formatArea(p.area_m2)],
    p.soil_type && ['نوع خاک', p.soil_type],
    ['مزرعه', <Link key="farm" to={`/farms/${p.farm.id}`} className="text-primary">{p.farm.name}</Link>],
    p.description && ['توضیحات', p.description],
  ].filter(Boolean)

  const next = p.next_operations ?? []
  const recent = p.recent_operations ?? []

  return (
    <Page>
      {/* بازگشت به مزرعه */}
      <Link to={`/farms/${p.farm.id}`} className="inline-flex items-center gap-1 text-sm text-muted hover:text-primary">
        <ChevronRight size={16} />
        {p.farm.name}
      </Link>

      <h1 className="text-center text-2xl font-bold">{p.name}</h1>

      <Card title="وضعیت کنونی">
        <div className="mb-5 grid grid-cols-2 gap-3">
          <Stat value={p.today_count} label="اقدام امروز" hint="در انتظار انجام" className="text-soil" />
          <Stat value={p.overdue_count} label="عقب‌افتاده" hint="موعد گذشته، انجام‌نشده" className="text-late" />
        </div>
        <InfoRows rows={status} />
      </Card>

      <SectionTitle>اقدامات بعدی</SectionTitle>
      {next.length === 0 ? (
        <p className="text-center text-sm text-muted">اقدام برنامه‌ریزی‌شده‌ای وجود ندارد.</p>
      ) : (
        <ul className="space-y-3">
          {next.map((op) => <OperationCard key={op.id} op={op} showPlace={false} onChange={plot.reload} />)}
        </ul>
      )}
      <SeeAll to={search('status=planned,in_progress&order=asc')}>تمام اقدامات آینده</SeeAll>

      <SectionTitle>عملیات‌های اخیر</SectionTitle>
      {recent.length === 0 ? (
        <p className="text-center text-sm text-muted">هنوز عملیاتی انجام نشده.</p>
      ) : (
        <ul className="space-y-3">
          {recent.map((op) => <OperationCard key={op.id} op={op} showPlace={false} onChange={plot.reload} />)}
        </ul>
      )}
      <SeeAll to={search('status=completed')}>تمام عملیات‌های گذشته</SeeAll>

      <SectionTitle>اطلاعات قطعه</SectionTitle>
      <Card>
        <InfoRows rows={info} />
        <button onClick={() => setEditing(true)} className="mt-4 flex items-center gap-2 text-sm font-medium text-primary">
          <Pencil size={16} />
          ویرایش
        </button>
      </Card>

      {editing && (
        <PlotFormModal
          farmId={p.farm.id}
          plot={p}
          onClose={() => setEditing(false)}
          onSaved={() => { setEditing(false); plot.reload() }}
        />
      )}
    </Page>
  )
}
