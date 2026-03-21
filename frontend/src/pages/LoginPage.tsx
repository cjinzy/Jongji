import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { MailRegular, LockClosedRegular, ArrowRightRegular } from '@fluentui/react-icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { loginApi, getMeApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'
import { setupApi } from '../api/teams'
import { DotGrid } from '../components/auth/DotGrid'
import { GoogleIcon } from '../components/auth/GoogleIcon'

export default function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldError, setFieldError] = useState('')

  const { data: setupStatus } = useQuery({
    queryKey: ['setup', 'status'],
    queryFn: setupApi.getStatus,
  })
  const setupCompleted = (setupStatus as { setup_completed?: boolean } | undefined)?.setup_completed
  const oauthAvailable = (setupStatus as { oauth_available?: boolean } | undefined)?.oauth_available ?? false

  // Setup 미완료 시 setup 페이지로 리다이렉트
  if (setupCompleted === false) {
    navigate('/setup', { replace: true })
    return null
  }

  const mutation = useMutation({
    mutationFn: async () => {
      const { access_token } = await loginApi({ email, password })
      const user = await getMeApi()
      return { access_token, user }
    },
    onSuccess: ({ access_token, user }) => {
      login(user, access_token)
      navigate('/', { replace: true })
    },
    onError: () => {
      setFieldError(t('auth.invalidCredentials'))
    },
  })

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setFieldError('')
    if (!email || !password) {
      setFieldError(t('auth.fieldRequired'))
      return
    }
    mutation.mutate()
  }

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center relative overflow-hidden">
      {/* Dot-grid background */}
      <DotGrid />

      <div className="relative z-10 w-full max-w-sm px-4">
        {/* Logo mark */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="w-9 h-9 bg-accent rounded-lg flex items-center justify-center shadow-lg shadow-accent/20">
            <span className="text-white font-bold text-sm tracking-tight">J</span>
          </div>
          <h1 className="text-text-primary text-xl font-semibold tracking-tight">
            {t('app.name')}
          </h1>
        </div>

        {/* Card */}
        <div
          className="bg-bg-secondary border border-border rounded-xl p-7 shadow-2xl"
          style={{ animation: 'fadeUp 0.35s ease both' }}
        >
          <h2 className="text-text-primary text-base font-medium mb-6">
            {t('auth.loginHeadline')}
          </h2>

          {/* Google OAuth button */}
          <button
            type="button"
            onClick={() => {
              if (oauthAvailable) window.location.href = '/api/v1/auth/google/authorize'
            }}
            disabled={!oauthAvailable}
            className={`w-full flex items-center justify-center gap-2.5 h-10 rounded-lg border border-border bg-bg-tertiary text-text-secondary text-sm font-medium transition-all duration-150 ${
              oauthAvailable
                ? 'hover:bg-bg-hover hover:text-text-primary cursor-pointer'
                : 'cursor-not-allowed opacity-50'
            }`}
            title={oauthAvailable ? undefined : t('auth.oauthNotConfigured')}
          >
            <GoogleIcon />
            {t('auth.googleLogin')}
          </button>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-border" />
            <span className="text-text-tertiary text-xs font-mono uppercase tracking-widest">
              {t('auth.orEmail')}
            </span>
            <div className="flex-1 h-px bg-border" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate className="space-y-3">
            <div className="relative">
              <MailRegular
                className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none"
                style={{ fontSize: 16 }}
              />
              <input
                type="email"
                autoComplete="email"
                placeholder={t('auth.email')}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full h-10 pl-9 pr-3 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all duration-150"
              />
            </div>

            <div className="relative">
              <LockClosedRegular
                className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none"
                style={{ fontSize: 16 }}
              />
              <input
                type="password"
                autoComplete="current-password"
                placeholder={t('auth.password')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full h-10 pl-9 pr-3 rounded-lg bg-bg-tertiary border border-border text-text-primary text-sm placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-all duration-150"
              />
            </div>

            {fieldError && (
              <p className="text-danger text-xs pt-0.5 font-mono">{fieldError}</p>
            )}

            <button
              type="submit"
              disabled={mutation.isPending}
              className="w-full h-10 rounded-lg bg-accent text-white text-sm font-medium flex items-center justify-center gap-2 hover:bg-accent-hover transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed mt-1"
            >
              {mutation.isPending ? (
                <span className="text-xs font-mono">{t('common.loading')}</span>
              ) : (
                <>
                  {t('auth.login')}
                  <ArrowRightRegular style={{ fontSize: 15 }} />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer link */}
        <p className="text-center text-text-tertiary text-xs mt-5">
          {t('auth.noAccount')}{' '}
          <Link
            to="/register"
            className="text-accent hover:text-accent-hover transition-colors duration-150 font-medium"
          >
            {t('auth.register')}
          </Link>
        </p>
      </div>

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(14px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
