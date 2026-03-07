import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  PeopleRegular,
  BuildingRegular,
  ShieldRegular,
  InfoRegular,
} from '@fluentui/react-icons'
import { teamsApi } from '../api/teams'
import { adminApi, type GoogleOAuthSettings, type GoogleOAuthSettingsUpdate } from '../api/admin'

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
  const queryClient = useQueryClient()

  const [isEditing, setIsEditing] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [editForm, setEditForm] = useState<GoogleOAuthSettingsUpdate>({
    client_id: '',
    client_secret: '',
    redirect_uri: window.location.origin + '/api/v1/auth/google/callback',
  })

  const { data: oauthSettings, isLoading, isError } = useQuery<GoogleOAuthSettings>({
    queryKey: ['admin', 'oauth', 'google'],
    queryFn: adminApi.getGoogleOAuth,
    retry: false,
  })

  const updateMutation = useMutation({
    mutationFn: adminApi.updateGoogleOAuth,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'oauth', 'google'] })
      setIsEditing(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteGoogleOAuth,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'oauth', 'google'] })
      setShowDeleteConfirm(false)
    },
  })

  const handleEditOpen = () => {
    setEditForm({
      client_id: oauthSettings?.client_id ?? '',
      client_secret: '',
      redirect_uri: oauthSettings?.redirect_uri ?? window.location.origin + '/api/v1/auth/google/callback',
    })
    setIsEditing(true)
  }

  const handleSubmit = () => {
    if (!editForm.client_id || !editForm.client_secret) return
    updateMutation.mutate(editForm)
  }

  const isConfigured = !isError && oauthSettings != null

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">
        {t('admin.oauth.title', 'Google OAuth')}
      </h2>

      {isLoading && (
        <p className="text-xs text-text-tertiary font-mono">{t('common.loading')}</p>
      )}

      {!isLoading && !isConfigured && !isEditing && (
        <div className="border border-dashed border-border rounded-xl p-5 space-y-3">
          <p className="text-sm text-text-secondary">{t('admin.oauth.notConfigured')}</p>
          <button
            onClick={handleEditOpen}
            className="px-3 py-1.5 text-xs font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
          >
            {t('admin.oauth.configure')}
          </button>
        </div>
      )}

      {!isLoading && isConfigured && !isEditing && !showDeleteConfirm && (
        <div className="border border-border rounded-xl p-4 space-y-3">
          <InfoRow label={t('admin.oauth.clientId')} value={oauthSettings.client_id} />
          <InfoRow label={t('admin.oauth.redirectUri')} value={oauthSettings.redirect_uri} />
          <InfoRow label={t('admin.oauth.secretMasked')} value={oauthSettings.secret_masked} />
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleEditOpen}
              className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-bg-hover text-text-secondary transition-colors"
            >
              {t('admin.oauth.edit')}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-3 py-1.5 text-xs font-medium border border-danger/30 rounded-lg hover:bg-danger/5 text-danger transition-colors"
            >
              {t('common.delete')}
            </button>
          </div>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="border border-danger/30 rounded-xl p-4 space-y-3 bg-danger/5">
          <p className="text-sm text-text-primary">{t('admin.oauth.deleteConfirm')}</p>
          <div className="flex gap-2">
            <button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="px-3 py-1.5 text-xs font-medium bg-danger text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-colors"
            >
              {deleteMutation.isPending ? t('common.loading') : t('common.delete')}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-bg-hover text-text-secondary transition-colors"
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      )}

      {isEditing && (
        <div className="border border-border rounded-xl p-4 space-y-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-secondary uppercase tracking-wider">
              {t('admin.oauth.clientId')}
            </label>
            <input
              value={editForm.client_id}
              onChange={(e) => setEditForm((f) => ({ ...f, client_id: e.target.value }))}
              placeholder="1234567890-abc.apps.googleusercontent.com"
              className="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-secondary uppercase tracking-wider">
              {t('admin.oauth.clientSecret')}
            </label>
            <input
              type="password"
              value={editForm.client_secret}
              onChange={(e) => setEditForm((f) => ({ ...f, client_secret: e.target.value }))}
              placeholder="GOCSPX-..."
              className="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-text-secondary uppercase tracking-wider">
              {t('admin.oauth.redirectUri')}
            </label>
            <input
              value={editForm.redirect_uri}
              onChange={(e) => setEditForm((f) => ({ ...f, redirect_uri: e.target.value }))}
              className="w-full px-3 py-2 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all"
            />
          </div>
          {updateMutation.isError && (
            <p className="text-xs text-danger">{t('common.error')}</p>
          )}
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleSubmit}
              disabled={updateMutation.isPending || !editForm.client_id || !editForm.client_secret}
              className="px-3 py-1.5 text-xs font-medium bg-accent text-white rounded-lg hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {updateMutation.isPending ? t('common.loading') : t('common.save')}
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-bg-hover text-text-secondary transition-colors"
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      )}
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
