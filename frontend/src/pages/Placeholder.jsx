import { Link } from 'react-router-dom'

// صفحه‌ی موقت برای مسیرهایی که بعداً ساخته می‌شوند.
export default function Placeholder({ title }) {
  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-10">
      <h1 className="text-xl font-bold">{title}</h1>
      <p className="mt-2 text-sm text-muted">این صفحه هنوز ساخته نشده.</p>
      <Link to="/dashboard" className="mt-4 inline-block text-sm font-medium text-primary">
        بازگشت به داشبورد
      </Link>
    </main>
  )
}
