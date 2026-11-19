import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Pencil, Plus } from 'lucide-react'
import Card from '../components/Card.jsx'
import SectionTitle from '../components/SectionTitle.jsx'
import Stat from '../components/Stat.jsx'
import InfoRows from '../components/InfoRows.jsx'
import PlotCard from '../components/farms/PlotCard.jsx'
import PlotFormModal from '../components/farms/PlotFormModal.jsx'
import EditFarmModal from '../components/farms/EditFarmModal.jsx'
import useLoad from '../hooks/useLoad.js'
import { api } from '../api.js'
import { faNumber, formatArea } from '../utils/format.js'

const sum = (list, pick) => list.reduce((t, x) => t + (pick(x) || 0), 0)

const Page = ({ children }) => (
  <main className="mx-auto w-full max-w-2xl flex-1 space-y-5 px-4 py-6">{children}</main>
)

// key={id}: با عوض شدن مزرعه، صفحه از نو بارگذاری می‌شود
export default function FarmDetail() {
  const { id } = useParams()
  return <FarmDetailView key={id} id={id} />
}

function FarmDetailView({ id }) {
  const farm = useLoad(() => api.farm(id))
  const [modal, setModal] = useState(null) // 'plot' | 'edit' | null
  const f = farm.data

  if (!f) {
    return (
      <Page>
        {farm.loading ? (
          <>
            <div className="mx-auto h-8 w-40 animate-pulse rounded-xl bg-primary-soft" />
            <div className="h-36 animate-pulse rounded-2xl bg-primary-soft" />
            <div className="h-44 animate-pulse rounded-2xl bg-primary-soft" />
          </>
        ) : (
          <>
            <p className="text-sm text-danger">{farm.error}</p>
            <Link to="/farms" className="text-sm font-medium text-primary">بازگشت به مزرعه‌ها</Link>
          </>
        )}
      </Page>
    )
  }

  const plots = f.plots ?? []
  const closeModal = () => setModal(null)
  const reloadAfter = () => { closeModal(); farm.reload() }

  // اطلاعات کلی؛ فیلدهای اختیاری فقط وقتی مقدار دارند نمایش داده می‌شوند
  const crops = [...new Set(plots.map((p) => p.current_season?.crop_name).filter(Boolean))].join('، ')
  const location = [f.province, f.city].filter(Boolean).join('، ')
  const rows = [
    ['نام مزرعه', f.name],
    ['مساحت کل', plots.length ? formatArea(sum(plots, (p) => p.area_m2)) : '—'],
    ['تعداد قطعات', `${faNumber(plots.length)} قطعه`],
    ['محصولات', crops || '—'],
    location && ['موقعیت', location],
    f.address && ['آدرس', f.address],
    f.latitude != null && f.longitude != null && ['مختصات', <span dir="ltr">{f.latitude}, {f.longitude}</span>],
    f.description && ['توضیحات', f.description],
  ].filter(Boolean)

  return (
    <Page>
      <h1 className="text-center text-2xl font-bold">{f.name}</h1>

      <Card title="وضعیت کنونی">
        <div className="grid grid-cols-2 gap-3">
          <Stat
            value={sum(plots, (p) => p.today_count)}
            label="اقدام امروز"
            hint="در انتظار انجام"
            className="text-soil"
          />
          <Stat
            value={sum(plots, (p) => p.overdue_count)}
            label="عقب‌افتاده"
            hint="موعد گذشته، انجام‌نشده"
            className="text-late"
          />
        </div>
      </Card>

      <SectionTitle>قطعات زراعی</SectionTitle>

      {plots.length === 0 && (
        <p className="text-center text-sm text-muted">هنوز قطعه‌ای برای این مزرعه ثبت نشده.</p>
      )}
      <ul className="space-y-4">
        {plots.map((p) => <PlotCard key={p.id} plot={p} />)}
      </ul>
      <div className="flex justify-center">
        <button
          onClick={() => setModal('plot')}
          className="flex h-10 items-center gap-1.5 rounded-xl border border-primary px-4 text-sm font-medium text-primary transition hover:bg-primary-soft"
        >
          <Plus size={16} />
          افزودن قطعه زراعی
        </button>
      </div>

      <SectionTitle>اطلاعات مزرعه</SectionTitle>

      <Card>
        <InfoRows rows={rows} />
        <button
          onClick={() => setModal('edit')}
          className="mt-4 flex items-center gap-2 text-sm font-medium text-primary"
        >
          <Pencil size={16} />
          ویرایش
        </button>
      </Card>

      {modal === 'plot' && <PlotFormModal farmId={f.id} onClose={closeModal} onSaved={reloadAfter} />}
      {modal === 'edit' && <EditFarmModal farm={f} onClose={closeModal} onSaved={reloadAfter} />}
    </Page>
  )
}
