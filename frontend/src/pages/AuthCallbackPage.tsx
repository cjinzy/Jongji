import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import { getMeApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'

/**
 * Handles the OAuth callback redirect from the backend.
 * Expects ?token=<jwt> on success or ?error=<message> on failure.
 */
export default function AuthCallbackPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const login = useAuthStore((s) => s.login)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const token = searchParams.get('token')
    const error = searchParams.get('error')

    if (error) {
      setErrorMsg(error)
      return
    }

    if (!token) {
      setErrorMsg(t('common.error'))
      return
    }

    getMeApi()
      .then((user) => {
        login(user, token)
        navigate('/', { replace: true })
      })
      .catch(() => {
        setErrorMsg(t('common.error'))
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (errorMsg) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <div className="bg-bg-secondary border border-border rounded-xl p-8 max-w-sm w-full text-center space-y-4">
          <p className="text-sm text-danger font-mono">{errorMsg}</p>
          <button
            onClick={() => navigate('/login', { replace: true })}
            className="px-4 py-2 text-sm font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
          >
            {t('auth.login')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center">
      <p className="text-xs text-text-tertiary font-mono animate-pulse">{t('common.loading')}</p>
    </div>
  )
}
