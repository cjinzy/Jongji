import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  PersonRegular,
  LockClosedRegular,
  GlobeRegular,
  AlertBadgeRegular,
  LaptopRegular,
} from '@fluentui/react-icons'
import ProfileSection from './settings/ProfileSettings'
import SecuritySection from './settings/SecuritySettings'
import SessionsSection from './settings/SessionsSettings'
import LanguageSection from './settings/LanguageSettings'
import NotificationsSection from './settings/NotificationsSettings'

type Section = 'profile' | 'security' | 'sessions' | 'language' | 'notifications'

/**
 * User settings page.
 * Sections: Profile, Security, Sessions, Language, Notifications (DND).
 */
export default function SettingsPage() {
  const { t } = useTranslation()
  const [section, setSection] = useState<Section>('profile')

  const nav: { key: Section; label: string; icon: React.ElementType }[] = [
    { key: 'profile', label: t('settings.profile', 'Profile'), icon: PersonRegular },
    { key: 'security', label: t('settings.security', 'Security'), icon: LockClosedRegular },
    { key: 'sessions', label: t('settings.sessions', '활성 세션'), icon: LaptopRegular },
    { key: 'language', label: t('settings.language', 'Language'), icon: GlobeRegular },
    { key: 'notifications', label: t('settings.notifications', 'Notifications'), icon: AlertBadgeRegular },
  ]

  return (
    <div className="px-6 py-8 max-w-3xl mx-auto">
      <h1 className="text-xl font-semibold text-text-primary tracking-tight mb-6">
        {t('nav.settings')}
      </h1>

      <div className="flex gap-6">
        {/* Sidebar nav */}
        <nav className="w-40 flex-shrink-0">
          <ul className="space-y-0.5">
            {nav.map(({ key, label, icon: Icon }) => (
              <li key={key}>
                <button
                  type="button"
                  onClick={() => setSection(key)}
                  className={[
                    'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors duration-75',
                    section === key
                      ? 'bg-bg-tertiary text-text-primary'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover',
                  ].join(' ')}
                >
                  <Icon style={{ fontSize: 15 }} />
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {section === 'profile' && <ProfileSection />}
          {section === 'security' && <SecuritySection />}
          {section === 'sessions' && <SessionsSection />}
          {section === 'language' && <LanguageSection />}
          {section === 'notifications' && <NotificationsSection />}
        </div>
      </div>
    </div>
  )
}
