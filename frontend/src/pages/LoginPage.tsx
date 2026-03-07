import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { MailRegular, LockClosedRegular, ArrowRightRegular } from '@fluentui/react-icons'
import { useMutation, useQuery } from '@tanstack/react-query'
import { loginApi, getMeApi } from '../api/auth'
import { useAuthStore } from '../stores/auth'
import { setupApi } from '../api/teams'

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
  const oauthAvailable = (setupStatus as { oauth_available?: boolean } | undefined)?.oauth_available ?? false

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

function DotGrid() {
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

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  )
}
