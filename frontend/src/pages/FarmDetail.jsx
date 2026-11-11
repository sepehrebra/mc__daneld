import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import Card from '../components/Card.jsx'
import Field from '../components/Field.jsx'
import Button from '../components/Button.jsx'
import { api } from '../api.js'

export default function FarmDetail() {
  const { id } = useParams()
  const [farm, setFarm] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [plotError, setPlotError] = useState('')
  const plotForm = useForm()

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    setFarm(null)
    api.farm(id)
      .then((item) => {
        if (!active) return
        setFarm(item)
        setLoading(false)
      })
      .catch((err) => { if (active) { setError(err.message); setLoading(false) } })
    return () => { active = false }
  }, [id])

  const addPlot = async (values) => {
    setPlotError('')
    try {
      await api.createPlot(id, { name: values.name.trim(), area_m2: Number(values.area_m2) })
      plotForm.reset()
      setFarm(await api.farm(id))
    } catch (err) {
      setPlotError(err.message)
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
              {farm.plots.map((plot) => <li key={plot.id}>
                {plot.name} — {plot.area_m2} مترمربع
                {plot.current_season && <span> — {plot.current_season.crop_name}</span>}
              </li>)}
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
      </>}
    </main>
  )
}
