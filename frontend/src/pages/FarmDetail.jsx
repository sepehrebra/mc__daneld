import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import Card from '../components/Card.jsx'
import Field from '../components/Field.jsx'
import Select from '../components/Select.jsx'
import DateField from '../components/DateField.jsx'
import Button from '../components/Button.jsx'
import { api } from '../api.js'
import { toISO } from '../utils/date.js'

export default function FarmDetail() {
  const { id } = useParams()
  const [farm, setFarm] = useState(null)
  const [seasons, setSeasons] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [plotError, setPlotError] = useState('')
  const [seasonError, setSeasonError] = useState('')
  const plotForm = useForm()
  const seasonForm = useForm({ defaultValues: { plot_id: '', crop_name: '', start_date: null } })
  const selectedPlot = seasonForm.watch('plot_id')

  useEffect(() => {
    let active = true
    api.farms()
      .then((farms) => {
        if (!active) return
        setFarm(farms.find((item) => item.id === id) ?? null)
        setLoading(false)
      })
      .catch((err) => { if (active) { setError(err.message); setLoading(false) } })
    return () => { active = false }
  }, [id])

  useEffect(() => {
    if (!selectedPlot) { setSeasons([]); return }
    let active = true
    api.cropSeasons(selectedPlot)
      .then((items) => { if (active) setSeasons(items) })
      .catch((err) => { if (active) setSeasonError(err.message) })
    return () => { active = false }
  }, [selectedPlot])

  const addPlot = async (values) => {
    setPlotError('')
    try {
      await api.createPlot(id, { name: values.name.trim(), area_m2: Number(values.area_m2) })
      plotForm.reset()
      const farms = await api.farms()
      setFarm(farms.find((item) => item.id === id) ?? null)
    } catch (err) {
      setPlotError(err.message)
    }
  }

  const addSeason = async (values) => {
    setSeasonError('')
    try {
      await api.createCropSeason(values.plot_id, {
        crop_name: values.crop_name.trim(), start_date: toISO(values.start_date),
      })
      const items = await api.cropSeasons(values.plot_id)
      setSeasons(items)
      seasonForm.setValue('crop_name', '')
      seasonForm.setValue('start_date', null)
    } catch (err) {
      setSeasonError(err.message)
    }
  }

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 space-y-5 px-4 py-6">
      <Link to="/dashboard" className="text-sm text-primary">بازگشت به داشبورد</Link>
      {loading && <p>در حال بارگذاری...</p>}
      {error && <p className="text-danger">{error}</p>}
      {!loading && !error && !farm && <p>مزرعه پیدا نشد.</p>}
      {farm && <>
        <h1 className="text-2xl font-bold">{farm.name}</h1>
        <Card title="قطعه‌های مزرعه">
          {farm.plots.length === 0 ? <p className="text-muted">هنوز قطعه‌ای ثبت نشده است.</p> : (
            <ul className="space-y-2">
              {farm.plots.map((plot) => <li key={plot.id}>{plot.name} — {plot.area_m2} مترمربع</li>)}
            </ul>
          )}
        </Card>
        <Card title="افزودن قطعه">
          <form onSubmit={plotForm.handleSubmit(addPlot)} className="space-y-4">
            <Field label="نام قطعه" error={plotForm.formState.errors.name?.message}
              {...plotForm.register('name', { required: 'نام قطعه را وارد کن' })} />
            <Field label="مساحت (مترمربع)" type="number" step="any" min="0.01"
              error={plotForm.formState.errors.area_m2?.message}
              {...plotForm.register('area_m2', { required: 'مساحت را وارد کن', min: { value: 0.01, message: 'مساحت باید مثبت باشد' } })} />
            {plotError && <p className="text-sm text-danger">{plotError}</p>}
            <Button type="submit" disabled={plotForm.formState.isSubmitting}>ثبت قطعه</Button>
          </form>
        </Card>
        {farm.plots.length > 0 && <Card title="ثبت دورهٔ کشت">
          <form onSubmit={seasonForm.handleSubmit(addSeason)} className="space-y-4">
            <Select label="قطعه" placeholder="انتخاب قطعه"
              error={seasonForm.formState.errors.plot_id?.message}
              {...seasonForm.register('plot_id', { required: 'قطعه را انتخاب کن' })}>
              {farm.plots.map((plot) => <option key={plot.id} value={plot.id}>{plot.name}</option>)}
            </Select>
            <Field label="نام محصول" error={seasonForm.formState.errors.crop_name?.message}
              {...seasonForm.register('crop_name', { required: 'نام محصول را وارد کن' })} />
            <DateField control={seasonForm.control} name="start_date" label="تاریخ شروع کشت"
              rules={{ required: 'تاریخ شروع را انتخاب کن' }}
              error={seasonForm.formState.errors.start_date?.message} />
            {seasonError && <p className="text-sm text-danger">{seasonError}</p>}
            <Button type="submit" disabled={seasonForm.formState.isSubmitting}>ثبت دورهٔ کشت</Button>
          </form>
          {seasons.length > 0 && <ul className="mt-4 space-y-1 text-sm">
            {seasons.map((season) => <li key={season.id}>{season.crop_name} — {season.start_date}</li>)}
          </ul>}
        </Card>}
      </>}
    </main>
  )
}
