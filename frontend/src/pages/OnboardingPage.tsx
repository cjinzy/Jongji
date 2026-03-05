import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import {
  PeopleTeamRegular,
  FolderRegular,
  RocketRegular,
  CheckmarkCircleRegular,
  BoardRegular,
  PersonAddRegular,
  LayerRegular,
} from '@fluentui/react-icons'
import { teamsApi } from '../api/teams'
import { useTeamStore } from '../stores/team'

function InputField({
  label,
  hint,
  optional,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string
  hint?: string
  optional?: boolean
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-text-secondary uppercase tracking-wider">
          {label}
        </label>
        {optional && (
          <span className="text-[10px] text-text-tertiary bg-bg-hover px-1.5 py-0.5 rounded">
            optional
          </span>
        )}
      </div>
      <input
        {...props}
        className="w-full px-3 py-2.5 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all duration-150"
      />
      {hint && <p className="text-xs text-text-tertiary">{hint}</p>}
    </div>
  )
}

function TipCard({
  icon: Icon,
  title,
  desc,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  desc: string
}) {
  return (
    <div className="flex gap-3 p-4 bg-bg-tertiary border border-border rounded-xl">
      <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
        <Icon className="w-4 h-4 text-accent" />
      </div>
      <div>
        <p className="text-sm font-medium text-text-primary">{title}</p>
        <p className="text-xs text-text-secondary mt-0.5">{desc}</p>
      </div>
    </div>
  )
}

export default function OnboardingPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { setTeams, setSelectedTeam, setProjects } = useTeamStore()

  const [step, setStep] = useState(0)
  const [mode, setMode] = useState<'create' | 'join'>('create')
  const [teamForm, setTeamForm] = useState({ name: '', description: '' })
  const [projectForm, setProjectForm] = useState({ name: '', key: '', description: '' })
  const [createdTeamId, setCreatedTeamId] = useState<string | null>(null)
  const [error, setError] = useState('')

  const createTeamMutation = useMutation({
    mutationFn: teamsApi.create,
    onSuccess: (team) => {
      setTeams([team])
      setSelectedTeam(team)
      setCreatedTeamId(team.id)
      setStep(1)
    },
    onError: () => setError('Failed to create team'),
  })

  const createProjectMutation = useMutation({
    mutationFn: ({ teamId, payload }: { teamId: string; payload: typeof projectForm }) =>
      teamsApi.createProject(teamId, payload),
    onSuccess: (project) => {
      setProjects([project])
      setStep(2)
    },
    onError: () => setError('Failed to create project'),
  })

  const deriveKey = (name: string) =>
    name
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 6) || ''

  const handleTeamNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value
    setTeamForm((f) => ({ ...f, name }))
  }

  const handleProjectNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const name = e.target.value
    setProjectForm((f) => ({ ...f, name, key: deriveKey(name) }))
  }

  const canProceedStep0 = mode === 'create' ? teamForm.name.trim().length > 0 : true
  const canProceedStep1 =
    projectForm.name.trim().length > 0 && projectForm.key.trim().length > 0

  const handleStep0Next = () => {
    if (mode === 'create') {
      createTeamMutation.mutate({ name: teamForm.name, description: teamForm.description })
    } else {
      // Join flow: skip for now, go to step 1
      setStep(1)
    }
  }

  const handleStep1Next = () => {
    if (!createdTeamId) {
      setStep(2)
      return
    }
    createProjectMutation.mutate({
      teamId: createdTeamId,
      payload: projectForm,
    })
  }

  const stepLabels = [
    t('onboarding.step1.label'),
    t('onboarding.step2.label'),
    t('onboarding.step3.label'),
  ]

  const isPending = createTeamMutation.isPending || createProjectMutation.isPending

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center p-4">
      {/* Background dots */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage: 'radial-gradient(var(--color-text-primary) 1px, transparent 1px)',
          backgroundSize: '28px 28px',
        }}
      />

      <div className="relative w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-accent/15 border border-accent/20 mb-4">
            <span className="text-accent font-black text-xl tracking-tighter">J</span>
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">
            {t('onboarding.title')}
          </h1>
          <p className="text-sm text-text-secondary mt-1">{t('onboarding.subtitle')}</p>
        </div>

        {/* Step dots */}
        <div className="flex justify-center gap-2 mb-8">
          {stepLabels.map((label, i) => (
            <div key={i} className="flex flex-col items-center gap-1.5">
              <div
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i === step
                    ? 'w-6 bg-accent'
                    : i < step
                    ? 'w-4 bg-accent/50'
                    : 'w-4 bg-bg-hover'
                }`}
              />
              <span
                className={`text-[10px] transition-colors duration-200 ${
                  i === step ? 'text-text-secondary' : 'text-text-tertiary'
                }`}
              >
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-bg-secondary border border-border rounded-2xl p-8 shadow-2xl">
          {/* Step 1: Team */}
          {step === 0 && (
            <div>
              <div className="flex items-start gap-3 mb-6">
                <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                  <PeopleTeamRegular className="w-4 h-4 text-accent" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-text-primary">
                    {t('onboarding.step1.title')}
                  </h2>
                </div>
              </div>

              {/* Tab switcher */}
              <div className="flex bg-bg-tertiary rounded-lg p-0.5 mb-5">
                {(['create', 'join'] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all duration-150 ${
                      mode === m
                        ? 'bg-bg-secondary text-text-primary shadow-sm'
                        : 'text-text-tertiary hover:text-text-secondary'
                    }`}
                  >
                    {m === 'create'
                      ? t('onboarding.step1.createTab')
                      : t('onboarding.step1.joinTab')}
                  </button>
                ))}
              </div>

              <div className="space-y-4 min-h-[120px]">
                {mode === 'create' ? (
                  <>
                    <InputField
                      label={t('onboarding.step1.teamName')}
                      placeholder={t('onboarding.step1.teamNamePlaceholder')}
                      value={teamForm.name}
                      onChange={handleTeamNameChange}
                      autoFocus
                    />
                    <InputField
                      label={t('onboarding.step1.teamDesc')}
                      placeholder={t('onboarding.step1.teamDescPlaceholder')}
                      value={teamForm.description}
                      onChange={(e) =>
                        setTeamForm((f) => ({ ...f, description: e.target.value }))
                      }
                      optional
                    />
                  </>
                ) : (
                  <InputField
                    label={t('onboarding.step1.inviteCode')}
                    placeholder={t('onboarding.step1.inviteCodePlaceholder')}
                    autoFocus
                  />
                )}
              </div>
            </div>
          )}

          {/* Step 2: Project */}
          {step === 1 && (
            <div>
              <div className="flex items-start gap-3 mb-6">
                <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                  <FolderRegular className="w-4 h-4 text-accent" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-text-primary">
                    {t('onboarding.step2.title')}
                  </h2>
                </div>
              </div>

              <div className="space-y-4 min-h-[160px]">
                <InputField
                  label={t('onboarding.step2.projectName')}
                  placeholder={t('onboarding.step2.projectNamePlaceholder')}
                  value={projectForm.name}
                  onChange={handleProjectNameChange}
                  autoFocus
                />
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-text-secondary uppercase tracking-wider">
                    {t('onboarding.step2.projectKey')}
                  </label>
                  <div className="relative">
                    <input
                      value={projectForm.key}
                      onChange={(e) =>
                        setProjectForm((f) => ({
                          ...f,
                          key: e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6),
                        }))
                      }
                      maxLength={6}
                      className="w-full px-3 py-2.5 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary font-mono placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/10 transition-all duration-150"
                      placeholder="MAIN"
                    />
                    {projectForm.key && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-tertiary">
                        {projectForm.key}-1
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-tertiary">
                    {t('onboarding.step2.projectKeyHint')}
                  </p>
                </div>
                <InputField
                  label={t('onboarding.step2.projectDesc')}
                  placeholder=""
                  value={projectForm.description}
                  onChange={(e) =>
                    setProjectForm((f) => ({ ...f, description: e.target.value }))
                  }
                  optional
                />
              </div>
            </div>
          )}

          {/* Step 3: Welcome */}
          {step === 2 && (
            <div>
              <div className="flex items-start gap-3 mb-6">
                <div className="w-8 h-8 rounded-lg bg-success/10 flex items-center justify-center shrink-0">
                  <RocketRegular className="w-4 h-4 text-success" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-text-primary">
                    {t('onboarding.step3.title')}
                  </h2>
                  <p className="text-xs text-text-secondary mt-0.5">
                    {t('onboarding.step3.desc')}
                  </p>
                </div>
              </div>

              <div className="space-y-2.5">
                <TipCard
                  icon={CheckmarkCircleRegular}
                  title={t('onboarding.step3.tip1Title')}
                  desc={t('onboarding.step3.tip1Desc')}
                />
                <TipCard
                  icon={PersonAddRegular}
                  title={t('onboarding.step3.tip2Title')}
                  desc={t('onboarding.step3.tip2Desc')}
                />
                <TipCard
                  icon={LayerRegular}
                  title={t('onboarding.step3.tip3Title')}
                  desc={t('onboarding.step3.tip3Desc')}
                />
              </div>
            </div>
          )}

          {error && (
            <p className="mt-4 text-xs text-danger bg-danger/5 border border-danger/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-6 pt-5 border-t border-border">
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2.5 text-sm text-text-tertiary hover:text-text-secondary transition-colors duration-150"
            >
              {t('onboarding.skipAll')}
            </button>

            <div className="flex-1" />

            {step > 0 && step < 2 && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="px-4 py-2.5 text-sm font-medium text-text-secondary border border-border rounded-lg hover:bg-bg-hover hover:text-text-primary transition-all duration-150"
              >
                {t('common.back')}
              </button>
            )}

            {step === 0 && (
              <button
                onClick={handleStep0Next}
                disabled={!canProceedStep0 || isPending}
                className="px-6 py-2.5 text-sm font-semibold text-white bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
              >
                {isPending ? t('common.loading') : t('common.next')}
              </button>
            )}

            {step === 1 && (
              <button
                onClick={handleStep1Next}
                disabled={!canProceedStep1 || isPending}
                className="px-6 py-2.5 text-sm font-semibold text-white bg-accent rounded-lg hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150"
              >
                {isPending ? t('common.loading') : t('common.next')}
              </button>
            )}

            {step === 2 && (
              <button
                onClick={() => navigate('/')}
                className="px-6 py-2.5 text-sm font-semibold text-white bg-accent rounded-lg hover:bg-accent-hover transition-all duration-150 flex items-center gap-2"
              >
                <BoardRegular className="w-4 h-4" />
                {t('onboarding.step3.goToApp')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
