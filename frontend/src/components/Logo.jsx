// لوگوی موقت (یک جوانه). بعداً با SVG یا تصویر لوگوی خودت جایگزین کن.
export default function Logo({ className = 'h-8 w-8' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="currentColor" />
      <path d="M16 25V15" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
      <path d="M16 16c0-4 2.5-6.5 7-6.5 0 4-2.5 6.5-7 6.5Z" fill="#fff" />
      <path d="M16 19c0-3-2-5-5.5-5 0 3 2 5 5.5 5Z" fill="#fff" fillOpacity=".75" />
    </svg>
  )
}
