/**
 * DotGrid — decorative dot-grid background used on auth pages.
 */
export function DotGrid() {
  return (
    <div
      className="pointer-events-none absolute inset-0"
      aria-hidden="true"
      style={{
        backgroundImage:
          'radial-gradient(circle, #2A2A2E 1px, transparent 1px)',
        backgroundSize: '28px 28px',
        opacity: 0.55,
      }}
    />
  )
}
