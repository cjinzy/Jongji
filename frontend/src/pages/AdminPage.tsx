import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  PeopleRegular,
  BuildingRegular,
  ShieldRegular,
  InfoRegular,
} from '@fluentui/react-icons'
import { teamsApi } from '../api/teams'

type Section = 'teams' | 'users' | 'security' | 'about'

/**
 * Admin settings page.
 * Shows server-wide configuration: teams, users, security, about.
 */
export default function AdminPage() {
  const { t } = useTranslation()
  const [section, setSection] = useState<Section>('teams')

  const nav: { key: Section; label: string; icon: React.ElementType }[] = [
    { key: 'teams', label: t('admin.teams', 'Teams'), icon: BuildingRegular },
    { key: 'users', label: t('admin.users', 'Users'), icon: PeopleRegular },
    { key: 'security', label: t('admin.security', 'Security'), icon: ShieldRegular },
    { key: 'about', label: t('admin.about', 'About'), icon: InfoRegular },
  ]

  return (
    <div className="px-6 py-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-2 mb-6">
        <ShieldRegular className="text-text-tertiary" style={{ fontSize: 18 }} />
        <h1 className="text-xl font-semibold text-text-primary tracking-tight">
          {t('admin.title', 'Admin')}
        </h1>
      </div>

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
          {section === 'teams' && <TeamsSection />}
          {section === 'users' && <UsersSection />}
          {section === 'security' && <SecuritySection />}
          {section === 'about' && <AboutSection />}
        </div>
      </div>
    </div>
  )
}

// ── Teams section ─────────────────────────────────────────────────────────────

function TeamsSection() {
  const { t } = useTranslation()
  const { data: teams, isLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: teamsApi.list,
  })

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('admin.teams', 'Teams')}
      </h2>

      {isLoading && (
        <p className="text-xs text-text-tertiary font-mono">{t('common.loading')}</p>
      )}

      <div className="space-y-2">
        {teams?.map((team) => (
          <div
            key={team.id}
            className="flex items-center gap-3 px-4 py-3 bg-bg-secondary border border-border rounded-lg"
          >
            <div className="w-7 h-7 rounded-md bg-bg-tertiary border border-border flex items-center justify-center flex-shrink-0">
              <span className="text-[9px] font-bold font-mono text-text-secondary">
                {team.key.slice(0, 3)}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-primary truncate">{team.name}</p>
              {team.description && (
                <p className="text-xs text-text-tertiary truncate">{team.description}</p>
              )}
            </div>
            <span className="text-[10px] font-mono text-text-tertiary bg-bg-tertiary border border-border rounded px-1.5 py-0.5">
              {team.key}
            </span>
          </div>
        ))}

        {!isLoading && teams?.length === 0 && (
          <p className="text-xs text-text-tertiary font-mono">
            {t('admin.noTeams', 'No teams yet')}
          </p>
        )}
      </div>
    </div>
  )
}

// ── Users section ─────────────────────────────────────────────────────────────

function UsersSection() {
  const { t } = useTranslation()
  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('admin.users', 'Users')}
      </h2>
      <Placeholder label={t('admin.comingSoon', 'User management coming soon')} />
    </div>
  )
}

// ── Security section ──────────────────────────────────────────────────────────

function SecuritySection() {
  const { t } = useTranslation()
  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('admin.security', 'Security')}
      </h2>
      <Placeholder label={t('admin.comingSoon', 'Security settings coming soon')} />
    </div>
  )
}

// ── About section ─────────────────────────────────────────────────────────────

function AboutSection() {
  const { t } = useTranslation()
  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('admin.about', 'About')}
      </h2>
      <div className="space-y-3">
        <InfoRow label="App" value="Jongji" />
        <InfoRow label="Version" value="0.1.0" />
        <InfoRow label="Framework" value="React 19 + Vite" />
        <InfoRow label="License" value="MIT" />
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function Placeholder({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center h-28 border border-dashed border-border rounded-xl">
      <p className="text-sm text-text-tertiary font-mono">{label}</p>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-4 px-4 py-2.5 bg-bg-secondary border border-border rounded-lg">
      <span className="text-xs font-mono text-text-tertiary w-20 flex-shrink-0">
        {label}
      </span>
      <span className="text-sm text-text-primary font-mono">{value}</span>
    </div>
  )
}
