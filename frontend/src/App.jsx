import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Footer from './components/Footer.jsx'
import AuthLayout from './components/AuthLayout.jsx'
import RequireAuth from './components/RequireAuth.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Placeholder from './pages/Placeholder.jsx'

// صفحه‌ای که لازم است کاربر وارد شده باشد
const Private = (title) => (
  <RequireAuth><Placeholder title={title} /></RequireAuth>
)

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/login" element={<AuthLayout><Login /></AuthLayout>} />
        <Route path="/register" element={<AuthLayout><Register /></AuthLayout>} />

        <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />

        {/* صفحه‌های بعدی: فعلاً موقت */}
        <Route path="/calendar" element={Private('تقویم کشاورزی')} />
        <Route path="/operations/recent" element={Private('عملیات‌های اخیر')} />
        <Route path="/operations/search" element={Private('نتایج جستجو')} />
        <Route path="/farms/new" element={Private('افزودن مزرعه')} />
        <Route path="/farms/:id" element={Private('مزرعه')} />
      </Routes>
      <Footer />
    </div>
  )
}
