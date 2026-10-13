import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import Card from '../components/Card.jsx'
import Field from '../components/Field.jsx'
import Button from '../components/Button.jsx'
import { api } from '../api.js'

export default function FarmNew() {
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm()

  const onSubmit = async ({ name }) => {
    setServerError('')
    try {
      const farm = await api.createFarm({ name: name.trim() })
      navigate(`/farms/${farm.id}`)
    } catch (error) {
      setServerError(error.message)
    }
  }

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 space-y-5 px-4 py-6">
      <Link to="/dashboard" className="text-sm text-primary">بازگشت به داشبورد</Link>
      <Card title="افزودن مزرعه">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field
            label="نام مزرعه"
            error={errors.name?.message}
            {...register('name', { required: 'نام مزرعه را وارد کن' })}
          />
          {serverError && <p className="text-sm text-danger">{serverError}</p>}
          <Button type="submit" disabled={isSubmitting}>ثبت مزرعه</Button>
        </form>
      </Card>
    </main>
  )
}
