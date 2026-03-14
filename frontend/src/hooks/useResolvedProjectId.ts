/**
 * useResolvedProjectId
 *
 * URL params(:teamId, :projKey)에서 slug(projKey)를 프로젝트 UUID로 변환합니다.
 * Sidebar와 동일한 query key(['projects', teamId])를 사용하여 캐시를 재활용합니다.
 */
import { useParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { teamsApi, type Project } from '../api/teams'

export interface ResolvedProjectId {
  /** URL param: 팀 UUID */
  teamId: string
  /** URL param: 프로젝트 slug (key) */
  projKey: string
  /** 매핑된 프로젝트 UUID. 로딩 중이거나 찾지 못한 경우 빈 문자열. */
  projectId: string
  /** 프로젝트 목록 로딩 여부 */
  isLoadingProjects: boolean
  /** 매핑된 Project 객체. 찾지 못한 경우 undefined. */
  project: Project | undefined
}

/**
 * URL params에서 teamId, projKey를 추출하고,
 * projKey(slug)를 프로젝트 UUID로 변환하여 반환합니다.
 *
 * Sidebar의 ['projects', teamId] 캐시를 공유하여 네트워크 요청을 최소화합니다.
 *
 * @returns ResolvedProjectId - teamId, projKey, projectId(UUID), 로딩 상태, project 객체
 */
export function useResolvedProjectId(): ResolvedProjectId {
  const { teamId = '', projKey = '' } = useParams<{
    teamId: string
    projKey: string
  }>()

  const { data: projects, isLoading: isLoadingProjects } = useQuery({
    queryKey: ['projects', teamId],
    queryFn: () => teamsApi.listProjects(teamId),
    enabled: !!teamId,
    staleTime: 5 * 60 * 1000, // 5분 — Sidebar 캐시 활용
  })

  const project = projects?.find((p) => p.key === projKey)
  const projectId = project?.id ?? ''

  return {
    teamId,
    projKey,
    projectId,
    isLoadingProjects,
    project,
  }
}
