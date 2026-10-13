import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import AuthCard from '../components/AuthCard.jsx'
import Field from '../components/Field.jsx'
import Button from '../components/Button.jsx'
import { api } from '../api.js'

export default function Register() {
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm()

  const onSubmit = async (data) => {
    setServerError('')
    try {
      await api.register(data)
      await api.login(data)
      navigate('/dashboard')
    } catch (error) {
      setServerError(error.message)
    }
  }

  return (
    <AuthCard
      title="ساخت حساب"
      subtitle="در چند ثانیه شروع کن و مزرعه‌ات را ثبت کن."
      footer={<>حساب داری؟ <Link to="/login" className="font-medium text-primary">وارد شو</Link></>}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <Field
          label="نام و نام خانوادگی"
          autoComplete="name"
          error={errors.name?.message}
          {...register('name', { required: 'نام را وارد کن' })}
        />
        <Field
          label="شماره موبایل"
          type="tel"
          dir="ltr"
          inputMode="numeric"
          autoComplete="tel"
          placeholder="09123456789"
          error={errors.phone?.message}
          {...register('phone', {
            required: 'شماره موبایل را وارد کن',
            pattern: { value: /^09\d{9}$/, message: 'شماره موبایل معتبر نیست' },
          })}
        />
        <Field
          label="رمز عبور"
          type="password"
          dir="ltr"
          autoComplete="new-password"
          error={errors.password?.message}
          {...register('password', {
            required: 'رمز عبور را وارد کن',
            minLength: { value: 8, message: 'رمز عبور حداقل ۸ کاراکتر باشد' },
          })}
        />
        <Field
          label="تکرار رمز عبور"
          type="password"
          dir="ltr"
          autoComplete="new-password"
          error={errors.confirm?.message}
          {...register('confirm', {
            required: 'رمز را دوباره وارد کن',
            validate: (v) => v === watch('password') || 'رمزها یکسان نیستند',
          })}
        />
        {serverError && <p className="text-sm text-danger">{serverError}</p>}
        <Button type="submit" disabled={isSubmitting}>ثبت‌نام</Button>
      </form>
    </AuthCard>
  )
}
