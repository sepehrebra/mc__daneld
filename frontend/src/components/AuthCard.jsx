// قاب مشترک صفحه‌های ورود و ثبت‌نام
export default function AuthCard({ title, subtitle, children, footer }) {
  return (
    <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 shadow-sm sm:p-8">
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="mt-1 text-sm text-muted">{subtitle}</p>
      <div className="mt-6">{children}</div>
      <p className="mt-6 text-center text-sm text-muted">{footer}</p>
    </div>
  )
}
