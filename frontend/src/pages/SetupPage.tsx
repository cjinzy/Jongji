import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import {
  PersonRegular,
  AppGenericRegular,
  CheckmarkCircleRegular,
  KeyRegular,
  EyeRegular,
  EyeOffRegular,
} from '@fluentui/react-icons'
import { setupApi } from '../api/teams'

function StepIndicator({
  current,
  labels,
}: {
  current: number
  labels: string[]
}) {
  return (
    <div className="flex items-center justify-center gap-0 mb-10">
      {labels.map((label, i) => (
        <div key={i} className="flex items-center">
          <div className="flex flex-col items-center gap-1.5">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-300 ${
                i < current
                  ? 'bg-accent text-white'
                  : i === current
                  ? 'bg-accent text-white ring-4 ring-accent/20'
                  : 'bg-bg-hover text-text-tertiary'
              }`}
            >
              {i < current ? (
                <CheckmarkCircleRegular className="w-4 h-4" />
              ) : (
                i + 1
              )}
            </div>
            <span
              className={`text-[10px] font-medium tracking-wide whitespace-nowrap transition-colors duration-200 ${
                i === current ? 'text-text-primary' : 'text-text-tertiary'
              }`}
            >
              {label}
            </span>
          </div>
          {i < labels.length - 1 && (
            <div
              className={`w-16 h-px mx-2 mb-5 transition-colors duration-300 ${
                i < current ? 'bg-accent' : 'bg-border'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  )
}

function InputField({
  label,
  hint,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string
  hint?: string
}) {
  const [showPw, setShowPw] = useState(false)
  const isPassword = props.type === 'password'

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-text-secondary uppercase tracking-wider">
        {label}
      </label>
      <div className="relative">
        <input
          {...props}
          type={isPassword && showPw ? 'text' : props.type}
          className="w-full px-3 py-2.5 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all duration-150 pr-10"
        />
        {isPassword && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShowPw((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary hover:text-text-secondary transition-colors"
          >
            {showPw ? (
              <EyeOffRegular className="w-4 h-4" />
            ) : (
              <EyeRegular className="w-4 h-4" />
            )}
          </button>
        )}
      </div>
      {hint && <p className="text-xs text-text-tertiary">{hint}</p>}
    </div>
  )
}

export default function SetupPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    admin_name: '',
    admin_email: '',
    admin_password: '',
    app_name: 'Jongji',
    google_client_id: '',
    google_client_secret: '',
    google_redirect_uri: window.location.origin + '/api/v1/auth/google/callback',
  })
  const [error, setError] = useState('')

  const { mutate: submit, isPending } = useMutation({
    mutationFn: setupApi.init,
    onSuccess: () => navigate('/login'),
    onError: () => setError(t('setup.error')),
  })

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  const stepLabels = [
    t('setup.step1.label'),
    t('setup.step2.label'),
    t('setup.step3.label'),
    t('setup.step4.label'),
  ]

  const stepIcons = [PersonRegular, AppGenericRegular, KeyRegular, CheckmarkCircleRegular]

  const canProceed = () => {
    if (step === 0) {
      return (
        form.admin_name.trim() &&
        form.admin_email.trim() &&
        form.admin_password.length >= 8
      )
    }
    if (step === 1) return form.app_name.trim().length > 0
    if (step === 2) return true
    return true
  }

  const handleNext = () => {
    if (step < 3) {
      setStep((s) => s + 1)
    } else {
      const payload: Record<string, unknown> = { ...form }
      if (!payload.google_client_id) delete payload.google_client_id
      if (!payload.google_client_secret) delete payload.google_client_secret
      if (!payload.google_client_id) delete payload.google_redirect_uri
      submit(payload as unknown as Parameters<typeof submit>[0])
    }
  }

  const CurrentIcon = stepIcons[step]

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      {/* Background grid texture */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.02]"
        style={{
          backgroundImage:
            'linear-gradient(var(--color-text-primary) 1px, transparent 1px), linear-gradient(90deg, var(--color-text-primary) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-full max-w-md">
        {/* Logo area */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-accent/15 border border-accent/20 mb-4">
            <span className="text-accent font-black text-xl tracking-tighter">J</span>
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">
            {t('setup.title')}
          </h1>
          <p className="text-sm text-text-secondary mt-1">{t('setup.subtitle')}</p>
        </div>

        {/* Card */}
        <div className="bg-bg-secondary border border-border rounded-2xl p-8 shadow-2xl">
          <StepIndicator current={step} labels={stepLabels} />

          {/* Step header */}
          <div className="flex items-start gap-3 mb-6">
            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0 mt-0.5">
              <CurrentIcon className="w-4 h-4 text-accent" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-text-primary">
                {step === 3 ? t('setup.step4.title' as never) : t(`setup.step${step + 1}.title` as never)}
              </h2>
              <p className="text-xs text-text-secondary mt-0.5">
                {step === 3 ? t('setup.step4.desc' as never) : t(`setup.step${step + 1}.desc` as never)}
              </p>
            </div>
          </div>

          {/* Step content */}
          <div className="space-y-4 min-h-[180px]">
            {step === 0 && (
              <>
                <InputField
                  label={t('setup.step1.adminName')}
                  placeholder="Jane Doe"
                  value={form.admin_name}
                  onChange={set('admin_name')}
                  autoFocus
                />
                <InputField
                  label={t('setup.step1.adminEmail')}
                  type="email"
                  placeholder="admin@example.com"
                  value={form.admin_email}
                  onChange={set('admin_email')}
                />
                <InputField
                  label={t('setup.step1.adminPassword')}
                  type="password"
                  placeholder="••••••••"
                  value={form.admin_password}
                  onChange={set('admin_password')}
                  hint={t('setup.step1.passwordHint')}
                />
              </>
            )}

            {step === 1 && (
              <InputField
                label={t('setup.step2.appName')}
                placeholder={t('setup.step2.appNamePlaceholder')}
                value={form.app_name}
                onChange={set('app_name')}
                autoFocus
              />
            )}

            {step === 2 && (
              <div className="space-y-4">
                <InputField
                  label={t('setup.step3.clientId')}
                  placeholder="1234567890-abc.apps.googleusercontent.com"
                  value={form.google_client_id}
                  onChange={set('google_client_id')}
                  autoFocus
                />
                <InputField
                  label={t('setup.step3.clientSecret')}
                  type="password"
                  placeholder="GOCSPX-..."
                  value={form.google_client_secret}
                  onChange={set('google_client_secret')}
                />
                <InputField
                  label={t('setup.step3.redirectUri')}
                  value={form.google_redirect_uri}
                  onChange={set('google_redirect_uri')}
                />
                <p className="text-xs text-text-tertiary">{t('setup.step3.skipHint')}</p>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-3">
                <div className="bg-bg-tertiary border border-border rounded-xl p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-text-tertiary uppercase tracking-wider font-medium">
                      {t('setup.step4.adminAccount')}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-text-primary">{form.admin_name}</p>
                    <p className="text-xs text-text-secondary">{form.admin_email}</p>
                  </div>
                </div>
                <div className="bg-bg-tertiary border border-border rounded-xl p-4">
                  <span className="text-xs text-text-tertiary uppercase tracking-wider font-medium block mb-2">
                    {t('setup.step4.appName')}
                  </span>
                  <p className="text-sm font-semibold text-text-primary">{form.app_name}</p>
                </div>
                <div className="bg-bg-tertiary border border-border rounded-xl p-4">
                  <span className="text-xs text-text-tertiary uppercase tracking-wider font-medium block mb-2">
                    {t('setup.step4.googleOAuth')}
                  </span>
                  <p className="text-sm font-semibold text-text-primary">
                    {form.google_client_id
                      ? t('setup.step4.googleOAuthConfigured')
                      : t('setup.step4.googleOAuthSkipped')}
                  </p>
                </div>
              </div>
            )}
          </div>

          {error && (
            <p className="mt-4 text-xs text-danger bg-danger/5 border border-danger/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-6 pt-5 border-t border-border">
            {step > 0 && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-text-secondary border border-border rounded-lg hover:bg-bg-hover hover:text-text-primary transition-all duration-150"
              >
                {t('common.back')}
              </button>
            )}
            {step === 2 && (
              <button
                onClick={() => {
                  setForm((f) => ({ ...f, google_client_id: '', google_client_secret: '' }))
                  setStep((s) => s + 1)
                }}
                className="flex-1 px-4 py-2.5 text-sm font-medium text-text-secondary border border-border rounded-lg hover:bg-bg-hover hover:text-text-primary transition-all duration-150"
              >
                {t('common.skip')}
              </button>
            )}
            <button
              onClick={handleNext}
              disabled={!canProceed() || isPending}
              className="flex-1 px-4 py-2.5 text-sm font-semibold text-white bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
            >
              {isPending
                ? t('common.loading')
                : step === 3
                ? t('setup.step4.submit')
                : t('common.next')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
