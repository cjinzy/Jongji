import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import {
  PersonRegular,
  LockClosedRegular,
  GlobeRegular,
  CheckmarkRegular,
} from '@fluentui/react-icons'
import { useAuthStore } from '../stores/auth'
import i18n from '../i18n'

type Section = 'profile' | 'security' | 'language'

/**
 * User settings page.
 * Sections: Profile, Security, Language.
 */
export default function SettingsPage() {
  const { t } = useTranslation()
  const [section, setSection] = useState<Section>('profile')

  const nav: { key: Section; label: string; icon: React.ElementType }[] = [
    { key: 'profile', label: t('settings.profile', 'Profile'), icon: PersonRegular },
    { key: 'security', label: t('settings.security', 'Security'), icon: LockClosedRegular },
    { key: 'language', label: t('settings.language', 'Language'), icon: GlobeRegular },
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
          {section === 'language' && <LanguageSection />}
        </div>
      </div>
    </div>
  )
}

// ── Profile ───────────────────────────────────────────────────────────────────

function ProfileSection() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const [name, setName] = useState(user?.name ?? '')
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: async () => {
      // TODO: wire to PATCH /users/me
      await new Promise((r) => setTimeout(r, 400))
    },
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    mutation.mutate()
  }

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('settings.profile', 'Profile')}
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Avatar placeholder */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-14 h-14 rounded-full bg-bg-tertiary border border-border flex items-center justify-center">
            <span className="text-lg font-bold text-text-secondary font-mono">
              {(user?.name ?? 'U')[0].toUpperCase()}
            </span>
          </div>
          <div>
            <p className="text-sm text-text-primary">{user?.name}</p>
            <p className="text-xs text-text-tertiary font-mono">{user?.email}</p>
          </div>
        </div>

        <Field label={t('settings.displayName', 'Display name')}>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full h-9 px-3 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all duration-150"
          />
        </Field>

        <Field label={t('auth.email')}>
          <input
            type="email"
            value={user?.email ?? ''}
            disabled
            className="w-full h-9 px-3 rounded-lg bg-bg-tertiary border border-border text-text-tertiary text-sm cursor-not-allowed opacity-60"
          />
        </Field>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="h-8 px-4 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors duration-100 disabled:opacity-50"
          >
            {mutation.isPending ? t('common.loading') : t('common.save')}
          </button>
          {saved && (
            <span className="inline-flex items-center gap-1 text-success text-xs font-mono">
              <CheckmarkRegular style={{ fontSize: 13 }} />
              {t('settings.saved', 'Saved')}
            </span>
          )}
        </div>
      </form>
    </div>
  )
}

// ── Security ──────────────────────────────────────────────────────────────────

function SecuritySection() {
  const { t } = useTranslation()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('settings.security', 'Security')}
      </h2>

      <form
        onSubmit={(e) => e.preventDefault()}
        className="space-y-4"
      >
        <Field label={t('settings.currentPassword', 'Current password')}>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            className="w-full h-9 px-3 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all duration-150"
          />
        </Field>

        <Field label={t('settings.newPassword', 'New password')}>
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            className="w-full h-9 px-3 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all duration-150"
          />
        </Field>

        <div className="pt-2">
          <button
            type="submit"
            className="h-8 px-4 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors duration-100 opacity-50 cursor-not-allowed"
            disabled
            title="Coming soon"
          >
            {t('settings.changePassword', 'Change password')}
          </button>
        </div>
      </form>
    </div>
  )
}

// ── Language ──────────────────────────────────────────────────────────────────

const LANGS = [
  { code: 'ko', label: '한국어' },
  { code: 'en', label: 'English' },
]

function LanguageSection() {
  const { t, i18n: _i18n } = useTranslation()
  const [current, setCurrent] = useState(i18n.language)

  function changeLang(code: string) {
    i18n.changeLanguage(code)
    setCurrent(code)
    localStorage.setItem('jongji-lang', code)
  }

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('settings.language', 'Language')}
      </h2>

      <div className="space-y-2">
        {LANGS.map(({ code, label }) => (
          <button
            key={code}
            type="button"
            onClick={() => changeLang(code)}
            className={[
              'w-full flex items-center justify-between px-4 py-3 rounded-lg border text-sm transition-all duration-100',
              current === code
                ? 'border-accent/60 bg-accent/10 text-text-primary'
                : 'border-border bg-bg-tertiary text-text-secondary hover:bg-bg-hover hover:text-text-primary',
            ].join(' ')}
          >
            {label}
            {current === code && (
              <CheckmarkRegular className="text-accent" style={{ fontSize: 15 }} />
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Field ─────────────────────────────────────────────────────────────────────

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-mono text-text-tertiary uppercase tracking-wider">
        {label}
      </label>
      {children}
    </div>
  )
}
