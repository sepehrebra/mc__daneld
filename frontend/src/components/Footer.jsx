import { BRAND } from '../config.js'

export default function Footer() {
  return (
    <footer className="border-t border-line bg-surface py-4 text-center text-xs text-muted">
      © {BRAND.name}
    </footer>
  )
}
