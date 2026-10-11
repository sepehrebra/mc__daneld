// قاب صفحه‌های ورود و ثبت‌نام (پس‌زمینه‌ی شیار زمین، کارت وسط صفحه)
export default function AuthLayout({ children }) {
  return (
    <main className="furrows flex flex-1 items-start justify-center px-4 py-8 sm:items-center sm:py-12">
      {children}
    </main>
  )
}
