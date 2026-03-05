import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckmarkRegular } from '@fluentui/react-icons'
import i18n from '../../i18n'

export const LANGS = [
  { code: 'ko', label: '한국어' },
  { code: 'en', label: 'English' },
]

/**
 * Language selection section — switches app locale and persists choice.
 */
export default function LanguageSection() {
  const { t } = useTranslation()
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
