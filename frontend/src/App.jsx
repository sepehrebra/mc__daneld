import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Footer from './components/Footer.jsx'
import AuthLayout from './components/AuthLayout.jsx'
import RequireAuth from './components/RequireAuth.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Placeholder from './pages/Placeholder.jsx'
import FarmNew from './pages/FarmNew.jsx'
import FarmDetail from './pages/FarmDetail.jsx'
import OperationDetail from './pages/OperationDetail.jsx'
import OperationsPage from './pages/OperationsPage.jsx'

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

        {/* تقویم هنوز صفحهٔ موقت است. */}
        <Route path="/calendar" element={Private('تقویم کشاورزی')} />
        <Route path="/operations/recent" element={<RequireAuth><OperationsPage /></RequireAuth>} />
        <Route path="/operations/search" element={<RequireAuth><OperationsPage /></RequireAuth>} />
        <Route path="/operations/:id" element={<RequireAuth><OperationDetail /></RequireAuth>} />
        <Route path="/farms/new" element={<RequireAuth><FarmNew /></RequireAuth>} />
        <Route path="/farms/:id" element={<RequireAuth><FarmDetail /></RequireAuth>} />
      </Routes>
      <Footer />
    </div>
  )
}
