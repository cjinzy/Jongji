import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { KeyRegular, ShieldLockRegular } from '@fluentui/react-icons'
import Field from '../../components/Field'

/**
 * Security settings section — password change, passkey, and 2FA stubs.
 */
export default function SecuritySection() {
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

      {/* ── Passkey / 2FA stubs ──────────────────────────────────────── */}
      <div className="mt-8 border-t border-border pt-6 space-y-4">
        <h3 className="text-xs font-mono text-text-tertiary uppercase tracking-wider mb-4">
          {t('settings.advancedSecurity', '고급 보안')}
        </h3>

        {/* Passkey */}
        <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-bg-tertiary border border-border">
          <div className="flex items-center gap-3">
            <KeyRegular style={{ fontSize: 18 }} className="text-text-secondary flex-shrink-0" />
            <div>
              <p className="text-sm text-text-primary">Passkey</p>
              <p className="text-xs text-text-tertiary mt-0.5">
                {t('settings.passkeyDesc', '비밀번호 없이 생체인식 또는 보안 키로 로그인')}
              </p>
            </div>
          </div>
          <div title="Coming soon">
            <button
              type="button"
              disabled
              className="h-8 px-3 rounded-lg bg-bg-hover border border-border text-text-tertiary text-xs font-medium opacity-50 cursor-not-allowed"
            >
              {t('settings.register', '등록')}
            </button>
          </div>
        </div>

        {/* 2FA TOTP */}
        <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-bg-tertiary border border-border">
          <div className="flex items-center gap-3">
            <ShieldLockRegular style={{ fontSize: 18 }} className="text-text-secondary flex-shrink-0" />
            <div>
              <p className="text-sm text-text-primary">2FA (TOTP)</p>
              <p className="text-xs text-text-tertiary mt-0.5">
                {t('settings.totpDesc', 'Google Authenticator 등 앱으로 2단계 인증 설정')}
              </p>
            </div>
          </div>
          <div title="Coming soon">
            <button
              type="button"
              disabled
              className="h-8 px-3 rounded-lg bg-bg-hover border border-border text-text-tertiary text-xs font-medium opacity-50 cursor-not-allowed"
            >
              {t('settings.setup', '설정')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
