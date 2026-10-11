export default function Button({ children, ...props }) {
  return (
    <button
      className="h-12 w-full rounded-xl bg-primary text-base font-bold text-white transition hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-wheat disabled:opacity-60"
      {...props}
    >
      {children}
    </button>
  )
}
