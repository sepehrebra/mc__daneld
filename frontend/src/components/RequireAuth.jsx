import { Navigate } from 'react-router-dom'
import { isLoggedIn } from '../auth.js'

// اگر کاربر وارد نشده باشد به صفحه‌ی ورود می‌رود.
export default function RequireAuth({ children }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />
}
