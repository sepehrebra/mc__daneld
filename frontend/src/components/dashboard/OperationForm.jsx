import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import Card from '../Card.jsx'
import Field from '../Field.jsx'
import Select from '../Select.jsx'
import Button from '../Button.jsx'
import DateField from '../DateField.jsx'
import FarmPlotSelects from './FarmPlotSelects.jsx'
import { api } from '../../api.js'
import { toISO } from '../../utils/date.js'

const TYPES = [
  ['planting', 'کاشت'], ['irrigation', 'آبیاری'], ['fertilizing', 'کوددهی'],
  ['spraying', 'سم‌پاشی'], ['harvesting', 'برداشت'], ['other', 'سایر'],
]

export default function OperationForm({ farms }) {
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const [seasons, setSeasons] = useState([])
  const form = useForm({
    defaultValues: {
      title: '', operation_type: 'irrigation', scheduled_date: null,
      scheduled_time: '', farm: '', plot: '', crop_season_id: '',
    },
  })
  const { register, handleSubmit, control, watch, setValue, formState: { errors, isSubmitting } } = form
  const plotId = watch('plot')
  const noFarms = !farms.loading && !farms.error && (farms.data ?? []).length === 0

  useEffect(() => {
    setValue('crop_season_id', '')
    if (!plotId) { setSeasons([]); return }
    let active = true
    api.cropSeasons(plotId)
      .then((items) => { if (active) setSeasons(items) })
      .catch((error) => { if (active) setServerError(error.message) })
    return () => { active = false }
  }, [plotId, setValue])

  const onSubmit = async (values) => {
    setServerError('')
    try {
      const operation = await api.createOperation(values.plot, {
        title: values.title.trim(),
        operation_type: values.operation_type,
        scheduled_date: toISO(values.scheduled_date),
        scheduled_time: values.scheduled_time
          ? (values.scheduled_time.length === 5 ? `${values.scheduled_time}:00` : values.scheduled_time)
          : null,
        ...(values.crop_season_id && { crop_season_id: values.crop_season_id }),
      })
      navigate(`/operations/${operation.id}`)
    } catch (error) {
      setServerError(error.message)
    }
  }

  return (
    <Card title="ثبت عملیات">
      {farms.error && <p className="mb-3 text-sm text-danger">{farms.error}</p>}
      {noFarms ? (
        <p className="text-sm text-muted">
          برای ثبت عملیات، اول <Link to="/farms/new" className="font-medium text-primary">یک مزرعه اضافه کن</Link>.
        </p>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <Field label="نام عملیات" placeholder="مثلاً آبیاری"
            error={errors.title?.message}
            {...register('title', { required: 'نام عملیات را وارد کن' })} />
          <Select label="نوع عملیات" placeholder="انتخاب نوع"
            error={errors.operation_type?.message}
            {...register('operation_type', { required: 'نوع عملیات را انتخاب کن' })}>
            {TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </Select>
          <div className="grid gap-4 sm:grid-cols-2">
            <DateField control={control} name="scheduled_date" label="تاریخ برنامه‌ریزی‌شده"
              rules={{ required: 'تاریخ را انتخاب کن' }} error={errors.scheduled_date?.message} />
            <Field label="ساعت (اختیاری)" type="time" dir="ltr"
              {...register('scheduled_time')} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <FarmPlotSelects form={form} farms={farms} required />
          </div>
          {plotId && <Select label="دورهٔ کشت (اختیاری)" placeholder="بدون دورهٔ کشت"
            {...register('crop_season_id')}>
            {seasons.map((season) => <option key={season.id} value={season.id}>
              {season.crop_name} — {season.start_date}
            </option>)}
          </Select>}
          {serverError && <p className="text-sm text-danger">{serverError}</p>}
          <Button type="submit" disabled={isSubmitting}>ثبت عملیات</Button>
        </form>
      )}
    </Card>
  )
}
