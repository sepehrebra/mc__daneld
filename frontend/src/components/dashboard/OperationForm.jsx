import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import Card from '../Card.jsx'
import Field from '../Field.jsx'
import Button from '../Button.jsx'
import DateField from '../DateField.jsx'
import FarmPlotSelects from './FarmPlotSelects.jsx'
import { api } from '../../api.js'
import { toISO } from '../../utils/date.js'

const SUGGESTIONS = ['کاشت', 'آبیاری', 'کوددهی', 'سم‌پاشی', 'برداشت']

export default function OperationForm({ farms }) {
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const form = useForm({
    defaultValues: { name: '', start: null, end: null, farm: '', plot: '' },
  })
  const { register, handleSubmit, control, getValues, formState: { errors, isSubmitting } } = form

  const noFarms = !farms.loading && !farms.error && (farms.data ?? []).length === 0

  const onSubmit = async (v) => {
    setServerError('')
    try {
      await api.createOperation({
        name: v.name.trim(),
        start_date: toISO(v.start),
        end_date: toISO(v.end),
        farm: v.farm,
        plot: v.plot,
      })
      navigate('/operations/recent')
    } catch (e) {
      setServerError(e.message)
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
          <Field
            label="نام عملیات"
            list="operation-names"
            placeholder="مثلاً آبیاری"
            error={errors.name?.message}
            {...register('name', { required: 'نام عملیات را وارد کن' })}
          />
          <datalist id="operation-names">
            {SUGGESTIONS.map((s) => <option key={s} value={s} />)}
          </datalist>

          <div className="grid gap-4 sm:grid-cols-2">
            <DateField
              control={control}
              name="start"
              label="تاریخ شروع"
              rules={{ required: 'تاریخ شروع را انتخاب کن' }}
              error={errors.start?.message}
            />
            <DateField
              control={control}
              name="end"
              label="تاریخ پایان (اختیاری)"
              clearable
              rules={{
                validate: (end) =>
                  !end || !getValues('start') || toISO(end) >= toISO(getValues('start')) ||
                  'تاریخ پایان قبل از شروع است',
              }}
              error={errors.end?.message}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <FarmPlotSelects form={form} farms={farms} required />
          </div>

          {serverError && <p className="text-sm text-danger">{serverError}</p>}
          <Button type="submit" disabled={isSubmitting}>ثبت عملیات</Button>
        </form>
      )}
    </Card>
  )
}
