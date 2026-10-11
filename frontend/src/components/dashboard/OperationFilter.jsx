import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import Card from '../Card.jsx'
import Button from '../Button.jsx'
import DateField from '../DateField.jsx'
import FarmPlotSelects from './FarmPlotSelects.jsx'
import { toISO } from '../../utils/date.js'

export default function OperationFilter({ farms }) {
  const navigate = useNavigate()
  const form = useForm({ defaultValues: { range: [], farm: '', plot: '' } })
  const { handleSubmit, control } = form

  // فیلترها را در آدرس صفحه‌ی نتایج می‌گذاریم:
  // /operations/search?from=2026-09-23&to=2026-10-07&farm=1&plot=11
  const onSubmit = (v) => {
    const params = new URLSearchParams()
    if (v.range?.[0]) params.set('from', toISO(v.range[0]))
    if (v.range?.[1]) params.set('to', toISO(v.range[1]))
    if (v.farm) params.set('farm', v.farm)
    if (v.plot) params.set('plot', v.plot)
    navigate(`/operations/search?${params}`)
  }

  return (
    <Card title="جستجو در سوابق">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <DateField
          control={control}
          name="range"
          label="بازه‌ی تاریخ"
          placeholder="از تاریخ تا تاریخ"
          range
          clearable
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <FarmPlotSelects form={form} farms={farms} required={false} />
        </div>
        <Button type="submit">جستجو</Button>
      </form>
    </Card>
  )
}
