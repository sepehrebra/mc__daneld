import { Link, useNavigate, useLocation } from 'react-router-dom'
import Logo from './Logo.jsx'
import { BRAND } from '../config.js'
import { isLoggedIn } from '../auth.js'
import { api } from '../api.js'

export default function Navbar() {
  const navigate = useNavigate()
  useLocation() // با تغییر صفحه، وضعیت ورود دوباره بررسی می‌شود
  const loggedIn = isLoggedIn()

  const logout = async () => {
    try {
      await api.logout()
    } catch {
      // Local session is cleared even when the server cannot be reached.
    } finally {
      navigate('/login')
    }
  }

  return (
    <header className="border-b border-line bg-surface">
      <nav className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        {/* لوگو + نام شرکت؛ هر دو یک لینک‌اند */}
        <Link to={BRAND.href} className="flex items-center gap-2 text-primary">
          <Logo />
          <span className="text-lg font-bold text-ink">{BRAND.name}</span>
        </Link>

        <div className="flex items-center gap-1 text-sm">
          {loggedIn ? (
            <button onClick={logout} className="rounded-lg px-3 py-2 text-muted hover:text-primary">
              خروج
            </button>
          ) : (
            <>
              <Link to="/login" className="rounded-lg px-3 py-2 text-muted hover:text-primary">
                ورود
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-primary-soft px-3 py-2 font-medium text-primary hover:bg-primary hover:text-white"
              >
                ثبت‌نام
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
