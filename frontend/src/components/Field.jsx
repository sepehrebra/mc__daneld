import { forwardRef, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

// یک فیلد فرم با برچسب و پیام خطا.
// type="password" به‌صورت خودکار دکمه نمایش/مخفی کردن رمز دارد.
const Field = forwardRef(function Field({ label, error, type = 'text', ...props }, ref) {
  const [show, setShow] = useState(false)
  const isPassword = type === 'password'

  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium">{label}</label>
      <div className="relative">
        <input
          ref={ref}
          type={isPassword && show ? 'text' : type}
          className={`h-12 w-full rounded-xl border bg-surface px-3 text-base outline-none transition
            focus:border-primary focus:ring-2 focus:ring-wheat/60
            ${error ? 'border-danger' : 'border-line'}
            ${isPassword ? 'ps-3 pe-11' : ''}`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute inset-y-0 end-0 flex w-11 items-center justify-center text-muted"
            aria-label={show ? 'مخفی کردن رمز' : 'نمایش رمز'}
          >
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  )
})

export default Field
