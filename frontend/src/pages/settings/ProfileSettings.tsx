import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import { CheckmarkRegular } from '@fluentui/react-icons'
import { useAuthStore } from '../../stores/auth'
import Field from '../../components/Field'

/**
 * Profile settings section — display name and email fields.
 */
export default function ProfileSection() {
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
