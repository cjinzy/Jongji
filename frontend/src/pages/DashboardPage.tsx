import { useTranslation } from 'react-i18next'
import { DataHistogramRegular } from '@fluentui/react-icons'

/**
 * Dashboard view placeholder.
 * Analytics and charts planned for a future phase.
 */
export default function DashboardPage() {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
      <div className="w-12 h-12 rounded-xl bg-bg-tertiary border border-border flex items-center justify-center">
        <DataHistogramRegular
          className="text-text-tertiary"
          style={{ fontSize: 22 }}
        />
      </div>
      <div>
        <p className="text-sm font-medium text-text-primary mb-1">
          {t('nav.dashboard')}
        </p>
        <p className="text-xs text-text-tertiary font-mono">
          {t('common.comingSoon', 'Coming soon')}
        </p>
      </div>
    </div>
  )
}
