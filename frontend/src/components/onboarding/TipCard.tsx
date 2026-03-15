interface TipCardProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  desc: string
}

/**
 * Icon + title + description card used in the onboarding welcome step.
 */
export function TipCard({ icon: Icon, title, desc }: TipCardProps) {
  return (
    <div className="flex gap-3 p-4 bg-bg-tertiary border border-border rounded-xl">
      <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
        <Icon className="w-4 h-4 text-accent" />
      </div>
      <div>
        <p className="text-sm font-medium text-text-primary">{title}</p>
        <p className="text-xs text-text-secondary mt-0.5">{desc}</p>
      </div>
    </div>
  )
}
