export default function Card({ title, children }) {
  return (
    <section className="rounded-2xl border border-line bg-surface p-5 shadow-sm">
      {title && <h2 className="mb-4 text-lg font-bold">{title}</h2>}
      {children}
    </section>
  )
}
