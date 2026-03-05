# Jongji - 최종 구현 스펙

> **문서 이력**: 원본 설계 + 비판적 검토(Critical 7건, Major 13건 해소) + 심층 인터뷰 2차(19개 추가 결정) + Brainstorm(10개 Gap 보강) + 심층 인터뷰 3차(23개 추가 결정) 통합
> **최종 확정일**: 2026-03-05
> **상태**: APPROVED - 구현 시 이 문서만 참조

---

## 1. 프로젝트 개요

"Jongji"는 미니멀하면서도 핵심 기능만 갖춘 프로젝트 관리 및 이슈 트래킹 도구입니다.
Linear 스타일의 다크 테마 UI를 기본으로 하며, 키보드 중심 조작과 실시간 협업을 지원합니다.

---

## 2. 확정된 핵심 결정사항

### 2.1 아키텍처

| 항목 | 결정 | 사유 |
|------|------|------|
| DB | **PostgreSQL 전용** | tsvector, ENUM, GIN, LISTEN/NOTIFY 등 PG 전용 기능 광범위 사용 |
| EventBus | **PostgreSQL LISTEN/NOTIFY** | 멀티 인스턴스 배포 시 이벤트 공유. 추가 인프라 불필요 |
| Gantt Chart | **frappe-gantt 라이브러리 활용** | 직접 Canvas+SVG 구현은 과잉 엔지니어링 |
| task_counter | **SELECT ... FOR UPDATE** | 프로젝트 row lock. 번호 절대 건너뛰지 않음 |
| 알림 디제스트 | **DB 기반 (alert_logs 활용)** | alert_logs에 pending 저장 후 APScheduler 5분 배치 전송. 서버 재시작에도 유실 없음 |
| SSE 재연결 (5분 초과) | **TanStack Query refetch에 위임** | 5분 TTL 버퍼 초과 시 별도 catch-up 불필요. invalidateQueries로 전체 refetch |

### 2.2 인증/보안

| 항목 | 결정 | 사유 |
|------|------|------|
| 인증 | Google OAuth + 자체 가입 동시 지원 | |
| 계정 충돌 | **최초 로그인 측 소유권 보유 + 안내 UX** | 동일 이메일 다른 방식 시도 시 "이미 Google로 가입된 이메일입니다" 안내. 중복 계정 불허 |
| Refresh Token | **전용 refresh_tokens 테이블 + HttpOnly 쿠키** | |
| CSRF | **Double Submit Cookie** | Refresh Token 쿠키 저장 시 필수 |
| MCP 인증 | **사용자별 API Key 발급** (user_api_keys 테이블) | 사용자 구분, 감사 추적, 권한 검사 |
| 로그인 보안 | **Rate limit 10req/min + progressive delay (1/2/4/8초) + 10회 실패 시 15분 잠금** | |
| 비밀번호 정책 | **최소 8자 이상** | 길이만 검증. 복잡도 규칙 없음. 사용자 경험 우선 |
| 세션 관리 | **다중 로그인 허용 + 세션 관리 UI** | 설정에서 활성 세션 목록 확인 + 특정 세션 로그아웃 가능 |
| 선택적 보안 | Passkey/2FA (Phase 6) | |

### 2.3 상태 전이 (엄격한 순차 전이)

```
허용 전이 테이블:
{
  BACKLOG:  [TODO],
  TODO:     [PROGRESS, BACKLOG],
  PROGRESS: [REVIEW, TODO],        # blocked_by 검증 필수
  REVIEW:   [DONE, PROGRESS],      # 역방향 허용 (리워크)
  DONE:     [CLOSED, REOPEN],
  REOPEN:   [TODO],                # REOPEN -> TODO만 허용
  CLOSED:   []                     # 최종 상태
}

제약:
- PROGRESS 진입: blocked_by 업무가 모두 DONE/CLOSED여야 함
- 상태 변경 권한: 담당자, 프로젝트장, 팀장, Admin만 가능
- 건너뛰기 불가: TODO -> DONE, BACKLOG -> PROGRESS 등 불가
```

### 2.4 권한 매트릭스

| 동작 | Admin | 팀장 | 프로젝트장 | 팀원 |
|------|-------|------|-----------|------|
| 팀 CRUD | O | 자기 팀 | X | X |
| 팀원 관리 (직접 추가) | O | 자기 팀 | X | X |
| 팀 초대 링크 관리 | O | 자기 팀 | X | X |
| 프로젝트 CRUD | O | 자기 팀 | 자기 프로젝트 | X |
| 프로젝트 멤버 관리 | O | 자기 팀 | 자기 프로젝트 | X |
| 업무 생성 | O | O | O | O (소속 프로젝트) |
| 업무 수정 | O | O | O | **생성자 또는 담당자** |
| 업무 Archive | O | O | O | X |
| 업무 상태 변경 | O | O | O | 담당 업무만 |
| 업무 복제 | O | O | O | O (소속 프로젝트) |
| 코멘트 작성 | O | O | O | O (Watcher 포함) |
| 라벨 관리 | O | O | O | X |
| 템플릿 관리 | O | O | O | X |
| 알림 설정 | O (전역) | 팀 범위 | 프로젝트 범위 | 개인만 |
| Admin 지정 | O | X | X | X |
| 시스템 설정 | O | X | X | X |
| 감사 로그 조회 | O | X | X | X |
| GCal 연동 | O | O | O | X |

> **Watcher**: 코멘트 작성만 가능. 업무 수정/상태 변경 불가.
> **미할당 업무**: 상태 변경은 생성자/리더만. 프로젝트 멤버면 자기 할당 가능.

### 2.5 타임존

- 시스템 타임존: admin이 `system_settings`에서 설정 (기본 UTC)
- **개인 타임존 오버라이드**: users 테이블에 `timezone` 컬럼. NULL이면 시스템 타임존 사용
- 서버 저장: UTC. 프론트엔드에서 사용자 타임존으로 변환 표시

### 2.6 팀/프로젝트 정책

| 항목 | 결정 |
|------|------|
| 팀 필수 | **모든 프로젝트는 팀에 소속** (`projects.team_id` NOT NULL). 개인 프로젝트는 1인 팀으로 처리 |
| 팀 참여 | 초대 링크 (만료일 + 최대 사용 횟수) 또는 직접 추가 |
| 다중 팀 | 한 사용자가 여러 팀에 소속 가능 (팀별 다른 역할) |
| 프로젝트/팀 삭제 | **소프트 아카이브** (is_archived 플래그. 네비게이션에서 숨김. 복원 가능) |
| 팀 아카이브 캐스케이드 | **확인 다이얼로그 후 하위 프로젝트 자동 캐스케이드 아카이브** |
| 아카이브된 프로젝트 Key | **영구 점유** - 한번 사용된 key는 재사용 불가. UNIQUE 제약 유지 |
| 계정 탈퇴 | **소프트 비활성화** (is_active=FALSE, 데이터 유지, 담당 업무 미할당 전환, UI에서 '비활성 사용자' 표시) |

### 2.7 업무 정책

| 항목 | 결정 |
|------|------|
| 긴급도 | P1~P9 단일 레벨 (1=최고, 9=최저) |
| 업무 번호 | 프로젝트별 번호 (예: `PROJ-42`) |
| 의존성 | Blocked by만 지원 (Sub task 미지원) |
| 의존성 제한 | **직접 blocked_by 최대 10개 + 전체 체인 깊이 최대 20** |
| 삭제 정책 | 소프트 Archive (is_archived 플래그) + 의존성 자동 해제 |
| 업무 복제 | 복제 시 BACKLOG 상태 초기화, 새 번호 부여. blocked_by 관계 미복제 |
| 업무 템플릿 | 프로젝트별 템플릿 저장/사용 가능 |
| 데이터 Import | 불필요 (MCP로 대량 생성 가능) |
| 담당자 | **선택적 (NULL 허용), 프로젝트 멤버만 할당 가능** |
| 다중 담당자 | **불필요 - 단일 담당자만** (assignee_id 단일 UUID 유지) |
| @멘션 | **Phase 2b에서 구현** (tiptap mention 플러그인, 멘션된 사용자 자동 Watcher 등록 + 알림) |
| Time Tracking | **초기 버전 불필요** (향후 추가 가능) |

---

## 3. 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | Python 3.12, FastAPI, FastMCP, uv |
| Frontend | React 19, Vite, TypeScript, Zustand, TanStack Query |
| DB | **PostgreSQL 전용** |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Auth | Google OAuth2 + JWT (자체가입) + 선택적 Passkey/2FA |
| Realtime | FastAPI SSE + **PostgreSQL LISTEN/NOTIFY** EventBus |
| Scheduler | APScheduler + **PostgreSQL advisory lock** (멀티 인스턴스 중복 방지) |
| Search | PostgreSQL tsvector + **pg_trgm** (한국어 trigram 검색 주력) |
| MD Editor | **tiptap** (ProseMirror 기반, mention 플러그인, 이미지 paste) |
| Charts | **recharts** (React 선언적 API) |
| Gantt | **frappe-gantt** (의존성 화살표, 드래그 일정 조정, zoom) |
| Icons | @fluentui/react-icons |
| i18n | i18next + react-i18next |
| DnD | @dnd-kit/core (Kanban) |
| URL State | **nuqs** (필터 URL query params 동기화) |
| Routing | **React Router v7** |
| CSS | **Tailwind CSS v4** (다크 모드 네이티브 지원) |
| Infra | Docker, Docker Compose |
| Lint/Format | Ruff, ty (type checker) |
| Logging | loguru (**JSON 구조화 로깅**) |
| File Storage | 로컬 파일시스템 (기본) + S3 호환 (선택) |
| Rate Limiting | **slowapi** (100req/min 기본, 로그인 10req/min) |
| Error Format | **RFC 7807 Problem Details** |
| Pagination | **Cursor-based** (created_at + id) |
| Testing | pytest + **testcontainers-python** (실제 PG 컨테이너) |

---

## 4. 프로젝트 디렉토리 구조

```
Jongji/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── src/
│   │   └── jongji/
│   │       ├── __init__.py
│   │       ├── main.py                 # FastAPI app + FastMCP mount + SSE
│   │       ├── config.py               # Settings (pydantic-settings)
│   │       ├── database.py             # DB engine, session
│   │       ├── models/                 # SQLAlchemy models
│   │       │   ├── __init__.py
│   │       │   ├── user.py             # users, refresh_tokens, user_api_keys
│   │       │   ├── team.py             # teams, team_invites
│   │       │   ├── project.py
│   │       │   ├── task.py             # tasks, task_templates
│   │       │   ├── label.py
│   │       │   ├── attachment.py
│   │       │   ├── alert.py            # alert_configs, alert_logs
│   │       │   └── audit.py
│   │       ├── schemas/                # Pydantic schemas
│   │       │   ├── __init__.py
│   │       │   ├── common.py           # RFC 7807 ProblemDetail, CursorPage
│   │       │   ├── user.py
│   │       │   ├── team.py
│   │       │   ├── project.py
│   │       │   ├── task.py
│   │       │   ├── label.py
│   │       │   └── alert.py
│   │       ├── api/                    # FastAPI routers
│   │       │   ├── __init__.py
│   │       │   ├── deps.py             # Dependencies (auth, db session, permissions)
│   │       │   ├── auth.py
│   │       │   ├── users.py
│   │       │   ├── teams.py
│   │       │   ├── projects.py
│   │       │   ├── tasks.py
│   │       │   ├── labels.py
│   │       │   ├── tags.py
│   │       │   ├── comments.py
│   │       │   ├── attachments.py
│   │       │   ├── alerts.py
│   │       │   ├── export.py
│   │       │   ├── calendar.py
│   │       │   ├── rss.py
│   │       │   ├── search.py
│   │       │   ├── dashboard.py
│   │       │   ├── admin.py            # 시스템 설정, 감사 로그 레벨
│   │       │   ├── health.py           # /health, /ready 엔드포인트
│   │       │   └── events.py           # SSE endpoint
│   │       ├── services/               # Business logic (API + MCP 공유)
│   │       │   ├── __init__.py
│   │       │   ├── auth_service.py
│   │       │   ├── team_service.py
│   │       │   ├── project_service.py
│   │       │   ├── task_service.py
│   │       │   ├── label_service.py
│   │       │   ├── tag_service.py      # #태그 추출/검색
│   │       │   ├── search_service.py   # Full-text search + pg_trgm
│   │       │   ├── export_service.py
│   │       │   ├── calendar_service.py
│   │       │   ├── scheduler_service.py
│   │       │   ├── audit_service.py    # 감사 로그
│   │       │   ├── event_bus.py        # PG LISTEN/NOTIFY EventBus
│   │       │   ├── storage/            # 파일 저장소 추상화
│   │       │   │   ├── __init__.py
│   │       │   │   ├── base.py         # StorageBackend ABC
│   │       │   │   ├── local.py
│   │       │   │   └── s3.py
│   │       │   └── alert/
│   │       │       ├── __init__.py
│   │       │       ├── base.py         # AlertChannel ABC
│   │       │       ├── dispatcher.py   # asyncio.create_task + 3회 재시도
│   │       │       ├── email_smtp.py
│   │       │       ├── email_api.py    # SendGrid/Mailgun
│   │       │       ├── telegram.py
│   │       │       ├── discord.py
│   │       │       ├── google_chat.py
│   │       │       ├── slack.py
│   │       │       └── rss.py
│   │       ├── mcp/                    # MCP Server tools
│   │       │   ├── __init__.py
│   │       │   └── tools.py
│   │       └── cli/                    # MCP CLI Client (Phase 7)
│   │           ├── __init__.py
│   │           ├── main.py             # CLI 엔트리포인트
│   │           ├── client.py           # MCP SDK Client 래퍼
│   │           └── commands/           # 서브커맨드 (projects, tasks, search, etc.)
│   └── tests/
│       ├── conftest.py                 # testcontainers PG 설정
│       ├── test_auth.py
│       ├── test_teams.py
│       ├── test_projects.py
│       ├── test_tasks.py
│       ├── test_labels.py
│       ├── test_search.py
│       └── test_alerts.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts              # Tailwind CSS v4 설정
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── i18n/                       # i18next 설정
│       │   ├── index.ts
│       │   ├── ko.json
│       │   └── en.json
│       ├── api/                        # API client (axios/fetch)
│       │   └── sse.ts                  # SSE EventSource client
│       ├── components/
│       │   ├── layout/                 # 사이드바, 헤더, 네비게이션
│       │   ├── kanban/                 # Kanban 보드 (@dnd-kit) + Unassigned 필터 토글
│       │   ├── table/                  # Table 뷰
│       │   ├── gantt/                  # Gantt Chart (frappe-gantt)
│       │   ├── dashboard/              # 차트, 통계 (recharts)
│       │   ├── task/                   # 업무 상세 사이드 패널
│       │   ├── editor/                 # tiptap 에디터 + 이미지 paste + @멘션
│       │   ├── onboarding/             # 온보딩 마법사 (3단계)
│       │   └── common/                 # 공통 컴포넌트
│       ├── pages/
│       │   ├── LoginPage.tsx           # 미니멀 중앙 카드 (Google + 자체 로그인)
│       │   └── ...
│       ├── hooks/
│       │   └── useKeyboardShortcuts.ts # 키보드 단축키
│       ├── stores/                     # Zustand stores
│       └── types/
├── docker-compose.yml
├── docker-compose.dev.yml              # 전체 Docker Compose 개발 환경
├── Dockerfile.backend
├── Dockerfile.frontend
├── scripts/
│   └── backup.sh                      # pg_dump 백업 스크립트
└── CLAUDE.md
```

---

## 5. 데이터베이스 스키마 (23개 테이블)

### 5.1 `users`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| email | VARCHAR UNIQUE | |
| name | VARCHAR | |
| password_hash | VARCHAR NULL | 자체가입 시 사용 (최소 8자) |
| google_id | VARCHAR NULL UNIQUE | OAuth 시 사용 |
| avatar_url | VARCHAR NULL | |
| is_admin | BOOLEAN DEFAULT FALSE | system admin 여부 |
| is_active | BOOLEAN DEFAULT TRUE | 탈퇴 시 FALSE (소프트 비활성화) |
| locale | VARCHAR DEFAULT 'ko' | 언어 설정 (ko/en) |
| timezone | VARCHAR NULL | 개인 타임존 (NULL이면 시스템 타임존 사용) |
| daily_summary_time | TIME DEFAULT '00:00' | 일일 요약 시간 |
| onboarding_completed | BOOLEAN DEFAULT FALSE | 온보딩 마법사 완료 여부 |
| dnd_start | TIME NULL | 방해금지 시작 시각 (예: 22:00) |
| dnd_end | TIME NULL | 방해금지 종료 시각 (예: 08:00) |
| passkey_credential | JSON NULL | Passkey 등록 정보 |
| totp_secret | VARCHAR NULL | 2FA TOTP 시크릿 |
| login_fail_count | INTEGER DEFAULT 0 | 연속 로그인 실패 횟수 |
| locked_until | TIMESTAMP NULL | 계정 잠금 해제 시각 |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

> **계정 탈퇴**: is_active=FALSE 설정. 담당 업무는 미할당(assignee_id=NULL)으로 전환. 생성한 업무/코멘트는 유지되며 UI에서 '비활성 사용자'로 표시.

### 5.2 `system_settings` (관리자 전역 설정)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| key | VARCHAR PK | 설정 키 |
| value | TEXT | 설정 값 |
| updated_at | TIMESTAMP | |

> 주요 키: `setup_completed` (기본 false), `app_name` (기본 Jongji), `default_locale` (기본 en), `timezone` (기본 UTC), `audit_log_level` (minimal/standard/full), `storage_backend` (local/s3), `email_backend` (smtp/api), `alert_digest_minutes` (기본 5)

### 5.3 `teams`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| name | VARCHAR | |
| description | TEXT NULL | |
| is_archived | BOOLEAN DEFAULT FALSE | 소프트 아카이브 (하위 프로젝트 캐스케이드) |
| created_by | UUID FK->users | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### 5.4 `team_members`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| team_id | UUID FK->teams | |
| user_id | UUID FK->users | |
| role | ENUM('leader', 'member') | 팀장/팀원 |
| created_at | TIMESTAMP | |
| UNIQUE(team_id, user_id) | | |

### 5.5 `projects`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| team_id | UUID FK->teams **NOT NULL** | 팀 필수 (개인 프로젝트는 1인 팀으로 처리) |
| name | VARCHAR | |
| key | VARCHAR **UNIQUE** | 티켓 번호 접두사 (예: PROJ). **영구 점유 - 아카이브 후에도 재사용 불가** |
| description | TEXT NULL | |
| is_private | BOOLEAN DEFAULT FALSE | |
| is_archived | BOOLEAN DEFAULT FALSE | 소프트 아카이브 |
| owner_id | UUID FK->users | 프로젝트장 |
| task_counter | INTEGER DEFAULT 0 | 티켓 번호 시퀀스 (SELECT FOR UPDATE) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### 5.6 `project_members`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| project_id | UUID FK->projects | |
| user_id | UUID FK->users | |
| role | ENUM('leader', 'member') | 프로젝트장/팀원 |
| min_alert_priority | INTEGER DEFAULT 1 | 알림 최소 긴급도 |
| created_at | TIMESTAMP | |
| UNIQUE(project_id, user_id) | | |

### 5.7 `labels` (프로젝트별 라벨)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| project_id | UUID FK->projects | |
| name | VARCHAR | |
| color | VARCHAR | HEX 색상 코드 |
| created_at | TIMESTAMP | |
| UNIQUE(project_id, name) | | |

### 5.8 `tasks`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| project_id | UUID FK->projects | |
| number | INTEGER | 프로젝트 내 순번 |
| title | VARCHAR | |
| description | TEXT NULL | Markdown 지원 |
| status | ENUM('BACKLOG','TODO','PROGRESS','REVIEW','DONE','REOPEN','CLOSED') | |
| priority | INTEGER (1~9) | 1=최고, 9=최저 |
| creator_id | UUID FK->users | 생성자 |
| assignee_id | UUID FK->users **NULL** | 담당자 (선택적, 프로젝트 멤버만) |
| start_date | DATE NULL | |
| due_date | DATE NULL | |
| is_archived | BOOLEAN DEFAULT FALSE | |
| google_event_id | VARCHAR NULL | GCal 이벤트 ID |
| search_vector | tsvector | Full-text 검색용 (트리거 자동 업데이트) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| UNIQUE(project_id, number) | | |

### 5.9 `task_labels` (다대다)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| task_id | UUID FK->tasks | |
| label_id | UUID FK->labels | |
| PK(task_id, label_id) | | |

### 5.10 `task_tags` (#태그 자동 추출)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| task_id | UUID FK->tasks | |
| tag | VARCHAR | #제외한 태그명 |
| created_at | TIMESTAMP | |
| UNIQUE(task_id, tag) | | INDEX on tag |

### 5.11 `task_watchers` (CC/Watcher)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| task_id | UUID FK->tasks | |
| user_id | UUID FK->users | |
| PK(task_id, user_id) | | |

> **@멘션 연동**: 코멘트/설명에서 @멘션된 사용자는 자동으로 task_watchers에 등록

### 5.12 `task_relations` (Blocked by)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| task_id | UUID FK->tasks | 이 업무가 |
| blocked_by_task_id | UUID FK->tasks | 이 업무에 의해 블로킹됨 |
| created_at | TIMESTAMP | |
| UNIQUE(task_id, blocked_by_task_id) | | |

> **제한**: 직접 blocked_by 최대 10개, 전체 체인 깊이 최대 20
> **검증**: 의존성 추가 시 DFS 기반 순환 참조(사이클) 검증 필수

### 5.13 `task_comments`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| task_id | UUID FK->tasks | |
| user_id | UUID FK->users | |
| content | TEXT | Markdown (@멘션 포함) |
| search_vector | tsvector | 코멘트 검색용 (트리거 자동 업데이트) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### 5.14 `attachments` (파일 첨부)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| task_id | UUID FK->tasks NULL | |
| comment_id | UUID FK->task_comments NULL | |
| filename | VARCHAR | 원본 파일명 |
| storage_path | VARCHAR | 저장 경로/키 |
| content_type | VARCHAR | MIME type |
| size | BIGINT | 바이트 |
| uploaded_by | UUID FK->users | |
| is_temp | BOOLEAN DEFAULT FALSE | 임시 업로드 (24시간 후 cron 삭제) |
| created_at | TIMESTAMP | |

### 5.15 `task_history` (변경 이력 - 월별 파티셔닝 + 영구 보존)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| task_id | UUID FK->tasks | |
| user_id | UUID FK->users | |
| field | VARCHAR | 변경된 필드명 |
| old_value | TEXT NULL | |
| new_value | TEXT NULL | |
| created_at | TIMESTAMP | 파티셔닝 키 |

### 5.16 `audit_logs` (감사 로그 - 월별 파티셔닝 + 90일 TTL)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK->users NULL | |
| action | VARCHAR | login, logout, create_team, update_task 등 |
| resource_type | VARCHAR | user, team, project, task 등 |
| resource_id | UUID NULL | |
| details | JSON NULL | 추가 정보 |
| ip_address | VARCHAR NULL | |
| log_level | ENUM('minimal','standard','full') | 이 로그의 레벨 |
| source | VARCHAR DEFAULT 'api' | 'api' 또는 'mcp' (요청 출처) |
| created_at | TIMESTAMP | 파티셔닝 키 |

> `system_settings.audit_log_level` 이상의 로그만 저장
> 90일 초과 데이터는 cron으로 자동 삭제

### 5.17 `alert_configs` (사용자별 알림 설정)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK->users | |
| channel | ENUM('email','telegram','discord','google_chat','slack') | |
| is_enabled | BOOLEAN DEFAULT TRUE | |
| webhook_url | VARCHAR NULL | Discord/Slack/GChat용 (암호화) |
| chat_id | VARCHAR NULL | Telegram용 |
| config_json | JSON NULL | 채널별 추가 설정 |
| created_at | TIMESTAMP | |
| UNIQUE(user_id, channel) | | |

### 5.18 `google_calendar_configs` (프로젝트별)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| project_id | UUID FK->projects UNIQUE | 프로젝트별 1개 |
| calendar_id | VARCHAR | GCal ID |
| access_token | TEXT | 암호화 저장 |
| refresh_token | TEXT | 암호화 저장 |
| token_expiry | TIMESTAMP | |
| connected_by | UUID FK->users | 연결한 사용자 |
| created_at | TIMESTAMP | |

### 5.19 `refresh_tokens`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK->users | |
| token_hash | VARCHAR | bcrypt 해시 |
| expires_at | TIMESTAMP | |
| revoked_at | TIMESTAMP NULL | revoke 시 설정 |
| device_info | VARCHAR NULL | User-Agent 등 (세션 관리 UI 표시용) |
| created_at | TIMESTAMP | |

> **세션 관리**: 다중 로그인 허용. 설정 > 활성 세션에서 device_info 기반 목록 표시 + 특정 세션 로그아웃(revoke) 가능.

### 5.20 `user_api_keys` (MCP용)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK->users | |
| key_hash | VARCHAR | API Key 해시 |
| name | VARCHAR | 키 이름 (예: "Claude Desktop") |
| last_used_at | TIMESTAMP NULL | |
| expires_at | TIMESTAMP NULL | |
| is_active | BOOLEAN DEFAULT TRUE | |
| created_at | TIMESTAMP | |

### 5.21 `alert_logs` (알림 전송 기록 + 디제스트 큐)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK->users | 수신자 |
| channel | VARCHAR | email, telegram 등 |
| status | ENUM('pending','sent','failed') | pending: 디제스트 대기 |
| retry_count | INTEGER DEFAULT 0 | |
| error_message | TEXT NULL | |
| payload | JSON | 전송 내용 |
| created_at | TIMESTAMP | |

> **디제스트 구현**: 알림 발생 시 status='pending'으로 저장. APScheduler가 5분마다 pending 건을 그룹핑하여 배치 전송 후 status='sent' 업데이트.

### 5.22 `team_invites` (팀 초대 링크)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| team_id | UUID FK->teams | |
| created_by | UUID FK->users | 생성자 |
| token | VARCHAR UNIQUE | 초대 링크 토큰 |
| expires_at | TIMESTAMP | 만료일 |
| max_uses | INTEGER NULL | 최대 사용 횟수 (NULL=무제한) |
| use_count | INTEGER DEFAULT 0 | 현재 사용 횟수 |
| is_active | BOOLEAN DEFAULT TRUE | |
| created_at | TIMESTAMP | |

### 5.23 `task_templates` (프로젝트별 업무 템플릿)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| project_id | UUID FK->projects | |
| name | VARCHAR | 템플릿 이름 |
| title_template | VARCHAR | 제목 템플릿 |
| description | TEXT NULL | 상세 내용 템플릿 |
| priority | INTEGER (1~9) | 기본 긴급도 |
| tags | TEXT[] NULL | 기본 태그 |
| created_by | UUID FK->users | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### (RSS는 `task_history` + `audit_logs` 기반으로 동적 생성, 별도 테이블 불필요)

---

## 6. 인덱스 전략

### 복합 인덱스 (고빈도 쿼리 최적화)

```sql
-- Tasks 조회
CREATE INDEX idx_tasks_project_status ON tasks(project_id, status) WHERE NOT is_archived;
CREATE INDEX idx_tasks_assignee_status ON tasks(assignee_id, status) WHERE NOT is_archived;
CREATE INDEX idx_tasks_project_number ON tasks(project_id, number);

-- Tags
CREATE INDEX idx_task_tags_tag ON task_tags(tag);

-- Relations
CREATE INDEX idx_task_relations_blocked ON task_relations(blocked_by_task_id);

-- Audit/History
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX idx_task_comments_task ON task_comments(task_id, created_at);
CREATE INDEX idx_task_history_task ON task_history(task_id, created_at);

-- Full-text Search (tasks)
CREATE INDEX idx_tasks_search ON tasks USING GIN(search_vector);
CREATE INDEX idx_tasks_trigram_title ON tasks USING GIN(title gin_trgm_ops);

-- Full-text Search (comments - 별도 인덱스)
CREATE INDEX idx_comments_search ON task_comments USING GIN(search_vector);
CREATE INDEX idx_comments_trigram ON task_comments USING GIN(content gin_trgm_ops);

-- Attachments (임시 파일 정리용)
CREATE INDEX idx_attachments_temp ON attachments(is_temp, created_at) WHERE is_temp = TRUE;

-- Team Invites
CREATE INDEX idx_team_invites_token ON team_invites(token) WHERE is_active = TRUE;

-- Alert Logs (디제스트 배치 처리용)
CREATE INDEX idx_alert_logs_pending ON alert_logs(status, created_at) WHERE status = 'pending';
```

---

## 7. Full-text Search + pg_trgm

### PostgreSQL tsvector + trigram 활용

```sql
-- tasks 테이블 검색 벡터 트리거
CREATE TRIGGER tasks_search_update
BEFORE INSERT OR UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION
tsvector_update_trigger(search_vector, 'pg_catalog.simple', title, description);

-- task_comments 테이블 검색 벡터 트리거
CREATE TRIGGER comments_search_update
BEFORE INSERT OR UPDATE ON task_comments
FOR EACH ROW EXECUTE FUNCTION
tsvector_update_trigger(search_vector, 'pg_catalog.simple', content);

-- pg_trgm 확장 (한국어 부분 문자열 매칭)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 검색 전략
- **한국어**: pg_trgm trigram 매칭 주력 (별도 한국어 토크나이저 없음)
- **영어**: tsvector Full-text + pg_trgm 보조
- **검색 범위**:
  - 업무 제목+설명: tsvector + pg_trgm 부분 매칭
  - 코멘트: 별도 search_vector + 검색 시 UNION으로 합산
  - #태그: task_tags 테이블 정확 매칭
  - 라벨, 상태, 담당자, 긴급도: 필터
  - 프로젝트 키+번호: `PROJ-42` 정확 매칭

---

## 8. #태그 시스템

### 추출 로직
- 업무 제목/설명에서 `#태그명` 패턴을 정규식으로 추출
- 업무 생성/수정 시 `task_tags` 테이블에 동기화 (삭제 후 재삽입)
- 패턴: `#[a-zA-Z가-힣0-9_-]+` (공백/특수문자에서 종료)

### API
- `GET /api/v1/tags?project_id={id}` - 프로젝트 내 태그 목록 (사용 횟수 포함)
- `GET /api/v1/tags/{tag}/tasks` - 태그로 업무 모아보기
- 검색 API에서 `tag:버그` 형식 지원

---

## 9. 긴급도 시스템

P1(최고) ~ P9(최저) 단일 값. DB에는 `INTEGER(1~9)`.

| 레벨 | 라벨 | 색상 |
|------|------|------|
| P1 | Critical | #EF4444 (빨강) |
| P2 | Very High | #F97316 (주황-빨강) |
| P3 | High | #F59E0B (주황) |
| P4 | Medium-High | #EAB308 (노랑-주황) |
| P5 | Medium | #FBBF24 (노랑) |
| P6 | Medium-Low | #84CC16 (연두) |
| P7 | Low | #22C55E (초록) |
| P8 | Very Low | #3B82F6 (파랑) |
| P9 | Minimal | #6B7280 (회색) |

---

## 10. API 엔드포인트

모든 API는 `/api/v1` 접두사. 인증 필수 (JWT Bearer 또는 MCP API Key).

### 공통 규격

- **에러 포맷**: RFC 7807 Problem Details `{type, title, status, detail, errors}`
- **페이지네이션**: Cursor-based (created_at + id). `?cursor={cursor}&limit=50`
- **Rate Limiting**: 100req/min 기본, 로그인 10req/min (slowapi)

### Auth
- `POST /auth/register` - 자체 가입 (비밀번호 최소 8자)
- `POST /auth/login` - 이메일+비밀번호 로그인 (progressive delay + 잠금)
- `GET /auth/google` - Google OAuth 시작
- `GET /auth/google/callback` - OAuth 콜백
- `POST /auth/refresh` - JWT 갱신 (HttpOnly 쿠키 + CSRF)
- `POST /auth/passkey/register` - Passkey 등록 (Phase 6)
- `POST /auth/passkey/login` - Passkey 로그인 (Phase 6)
- `POST /auth/2fa/setup` - 2FA TOTP 설정 (Phase 6)
- `POST /auth/2fa/verify` - 2FA 검증 (Phase 6)

### Users
- `GET /users/me` - 내 정보
- `PUT /users/me` - 내 정보 수정 (locale, timezone, daily_summary_time, dnd_start/end 등)
- `DELETE /users/me` - 계정 비활성화 (소프트 탈퇴)
- `GET /users` - 사용자 검색 (Admin/팀장용, 팀 초대 시)
- `GET /users/me/api-keys` - 내 MCP API Key 목록
- `POST /users/me/api-keys` - MCP API Key 생성
- `DELETE /users/me/api-keys/{id}` - MCP API Key 삭제
- `GET /users/me/sessions` - 활성 세션 목록
- `DELETE /users/me/sessions/{id}` - 특정 세션 로그아웃 (refresh_token revoke)

### Teams
- `GET/POST /teams`
- `GET/PUT/DELETE /teams/{id}` (DELETE = 소프트 아카이브 + 하위 프로젝트 캐스케이드)
- `GET/POST/DELETE /teams/{id}/members`
- `POST /teams/{id}/invites` - 초대 링크 생성 (팀장/Admin)
- `GET /teams/{id}/invites` - 초대 링크 목록
- `DELETE /teams/{id}/invites/{inviteId}` - 초대 링크 비활성화
- `POST /teams/join/{token}` - 초대 링크로 팀 가입

### Projects
- `GET/POST /projects`
- `GET/PUT/DELETE /projects/{id}` (DELETE = 소프트 아카이브)
- `GET/POST/DELETE /projects/{id}/members`

### Labels
- `GET/POST /projects/{id}/labels`
- `PUT/DELETE /labels/{id}`

### Tasks
- `GET/POST /projects/{id}/tasks`
- `GET/PUT /tasks/{id}`
- `DELETE /tasks/{id}` -> Archive (is_archived=true + 의존성 자동 해제)
- `PATCH /tasks/{id}/status` - 상태 변경 (전이 테이블 검증 + Blocked by 검증 + 알림 트리거)
- `POST /tasks/{id}/clone` - 업무 복제 (BACKLOG 초기화, 새 번호, blocked_by 미복제)
- `GET/POST/DELETE /tasks/{id}/watchers`
- `GET/POST/DELETE /tasks/{id}/blocked-by` (최대 10개 제한 + DFS 순환 검증)
- `GET/POST /tasks/{id}/comments`
- `POST /tasks/{id}/comments/{id}/attachments` - 코멘트 첨부
- `POST /tasks/{id}/attachments` - 업무 첨부
- `POST /attachments/upload` - 임시 업로드 (에디터 이미지 paste용, 24h TTL)
- `GET /tasks/{id}/history`
- `GET /tasks/{id}/labels`
- `POST/DELETE /tasks/{id}/labels/{label_id}`

### Templates
- `GET /projects/{projectId}/templates` - 템플릿 목록
- `POST /projects/{projectId}/templates` - 템플릿 생성
- `PUT /projects/{projectId}/templates/{id}` - 템플릿 수정
- `DELETE /projects/{projectId}/templates/{id}` - 템플릿 삭제
- `POST /projects/{projectId}/templates/{id}/create-task` - 템플릿으로 업무 생성

### Tags
- `GET /tags?project_id={id}` - 태그 목록
- `GET /tags/{tag}/tasks` - 태그별 업무

### Search
- `GET /search?q={query}&project_id={id}&tag={tag}&status={status}&...`
- 검색 결과에 tasks + comments 모두 포함 (UNION)

### Export
- `GET /projects/{id}/export?format=json|markdown`
- `GET /tasks/{id}/export?format=json|markdown`

### Dashboard
- `GET /projects/{id}/dashboard` - 통계 + 차트 데이터 (실시간 SQL 집계)

### Alert
- `GET/PUT /users/me/alert-configs`
- `GET /projects/{id}/rss` - RSS Feed (XML)

### Calendar
- `POST /projects/{id}/calendar/connect` - 프로젝트별 GCal 연동
- `DELETE /projects/{id}/calendar/disconnect`

### Setup (시스템 초기 설정, setup 미완료 시에만 허용)
- `GET /setup/status` - setup 완료 여부 + OAuth 사용 가능 여부
- `POST /setup/admin` - Admin 계정 생성 (DB 트랜잭션 + Race Condition 방지)
- `POST /setup/settings` - 시스템 설정 저장 (app_name, timezone, default_locale)
- `POST /setup/complete` - setup 완료 처리 (seed 데이터 + setup_completed=true)

### Admin
- `GET/PUT /admin/settings` - 시스템 설정 (timezone, audit level 등)
- `GET /admin/audit-logs` - 감사 로그 조회
- `PUT /admin/users/{id}/role` - Admin 지정/해제 (**마지막 Admin 해제 시 409 Conflict**)

### Health
- `GET /health` - Docker healthcheck용
- `GET /ready` - 서비스 준비 상태

### SSE (실시간)
- `GET /events/stream?project_id={id}` - SSE 스트림 (Last-Event-Id 지원)

---

## 11. 인증/인가 설계

### 인증 흐름
1. **Google OAuth**: `/auth/google` -> Google 동의 -> callback -> JWT 발급
2. **자체 가입**: `/auth/register` -> 이메일+비밀번호 (최소 8자) -> JWT 발급
3. **계정 충돌**: 동일 이메일로 다른 방식 시도 시 **안내 메시지 + 기존 방식으로 유도**. 자동 병합 불가.
4. **Passkey/2FA**: 선택적 활성화 (Phase 6)

### JWT 구조
- Access Token: 15분 만료 (Authorization: Bearer)
- Refresh Token: 7일 만료 (HttpOnly 쿠키 + CSRF Double Submit Cookie)
- `refresh_tokens` 테이블에서 관리 (revoke 지원)

### 로그인 보안
- Rate Limiting: 10req/min (slowapi)
- Progressive Delay: 실패 시 1초 -> 2초 -> 4초 -> 8초 지연
- 계정 잠금: 10회 연속 실패 시 15분 잠금 (`users.locked_until`)
- 성공 시 `login_fail_count` 초기화
- 비밀번호 정책: 최소 8자 이상 (길이만 검증)

### 세션 관리
- 다중 디바이스 동시 로그인 허용
- `refresh_tokens.device_info`에 User-Agent 기록
- 설정 > 활성 세션 목록: device_info + created_at 표시
- 특정 세션 로그아웃: `DELETE /users/me/sessions/{id}` -> refresh_token revoke

### Setup Wizard (시스템 초기 설정)

서버 최초 실행 시 DB에 사용자가 0명이면 `/setup` 페이지로 리다이렉트되어 웹 UI 기반 Setup Wizard를 진행한다.

#### 진입 조건
- `system_settings`에 `setup_completed` 키가 없거나 값이 `false`일 때만 `/setup` 접근 가능
- `setup_completed=true`인 상태에서 `/setup` 접근 시 → `/login`으로 리다이렉트
- 모든 인증되지 않은 요청은 `/setup`으로 리다이렉트 (setup 미완료 시)

#### Race Condition 방지
- Admin 계정 생성을 DB 트랜잭션으로 감싸고, `users` 테이블에 첫 행이 이미 존재하면 실패
- 동시 접속 시 두 번째 요청은 "이미 셋업이 완료되었습니다" 메시지 + `/login` 리다이렉트

#### Wizard 단계 (3단계, 중앙 카드 + Stepper UI)

**Step 1: Admin 계정 생성 [필수]**
- Google OAuth 버튼 (환경변수 `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`이 설정되어 있을 때만 표시)
- 또는 이메일/비밀번호 자체가입 (비밀번호 최소 8자 검증 동일 적용)
- 이름, 아바타 설정
- 생성된 계정에 `is_admin=true` 자동 부여

**Step 2: 시스템 설정 [건너뛰기 가능]**
- 앱 이름 (기본: `Jongji`) → `system_settings.app_name`에 저장. 브라우저 타이틀 + 로그인 페이지에만 적용
- 시스템 타임존 (기본: `UTC`) → `system_settings.timezone`
- 기본 언어 (기본: `en`) → `system_settings.default_locale`
- 건너뛰기 시 모든 값은 기본값으로 저장

**Step 3: 완료 확인**
- 설정 요약 표시 (계정 정보, 시스템 설정값)
- "시작하기" 버튼 클릭 시:
  1. `system_settings.setup_completed = true` 저장
  2. 기본 라벨 seed 데이터 생성 (priority: Urgent/High/Medium/Low/None)
  3. 온보딩 마법사(13.10)로 진입 (프로필 → 팀 참여 → 프로젝트 참여)

#### Admin 불변성 규칙
- `is_admin=true`인 사용자가 1명일 때 해당 사용자의 탈퇴(`DELETE /users/me`) 및 admin 해제(`PUT /admin/users/{id}/role`) 차단
- 에러 응답: `409 Conflict` + `"최소 1명의 Admin이 필요합니다"`

#### Setup API
- `GET /setup/status` — setup 완료 여부 반환 (`{ "setup_completed": bool, "oauth_available": bool }`)
- `POST /setup/admin` — Admin 계정 생성 (setup 미완료 시에만 허용)
- `POST /setup/settings` — 시스템 설정 저장 (setup 미완료 시에만 허용)
- `POST /setup/complete` — setup 완료 처리 (seed 데이터 생성 + `setup_completed=true`)

---

## 12. SSE 실시간 업데이트

### EventBus: PostgreSQL LISTEN/NOTIFY 기반

```
서비스 계층 -> PG NOTIFY channel -> EventBus listener -> SSE StreamingResponse
```

- 멀티 인스턴스 배포 시 모든 인스턴스가 동일 이벤트 수신
- MCP를 통한 변경도 동일하게 SSE 이벤트 발행

### 이벤트 유형
| 이벤트 | 데이터 | 수신 범위 |
|--------|--------|-----------|
| `task.created` | task 객체 | 프로젝트 멤버 |
| `task.updated` | 변경 필드 + 값 | 프로젝트 멤버 |
| `task.status_changed` | task_id, old/new status | 프로젝트 멤버 |
| `task.moved` | task_id, old/new status | 프로젝트 멤버 (Kanban 반영) |
| `comment.created` | comment 객체 | 업무 관련자 |
| `task.archived` | task_id | 프로젝트 멤버 |

### SSE 재연결
- **Last-Event-Id**: 프로젝트당 최근 100개 이벤트 / 5분 TTL 메모리 버퍼
- 클라이언트 재연결 시 Last-Event-Id 이후 이벤트 재전송
- **5분 초과 오프라인**: TanStack Query의 invalidateQueries로 전체 refetch에 위임

### 동시 편집 전략
- **Last Write Wins**: 동시 편집 시 마지막 저장이 우선
- SSE로 다른 사용자 수정 **실시간 반영**
- 충돌 시 토스트 알림: "OOO님이 이 업무를 수정했습니다"

### 프론트엔드 상태 관리
| 영역 | 도구 | 예시 |
|------|------|------|
| 서버 데이터 | TanStack Query | 업무 목록, 프로젝트 정보, 댓글 |
| UI 상태 | Zustand | 사이드바 열림, 선택된 필터, 다크모드 |
| SSE 이벤트 | EventSource -> TanStack Query | `invalidateQueries`로 캐시 무효화 |

---

## 13. 프론트엔드 설계

### 13.1 URL 구조 (계층형, React Router v7)

```
/                                              # 홈 (대시보드/리다이렉트)
/setup                                         # Setup Wizard (최초 설치 시에만 접근 가능)
/login                                         # 로그인 (미니멀 중앙 카드)
/register                                      # 회원가입
/onboarding                                    # 온보딩 마법사 (최초 로그인)
/teams/{teamId}                                # 팀 상세
/teams/{teamId}/projects/{projKey}/kanban       # Kanban 뷰
/teams/{teamId}/projects/{projKey}/table        # Table 뷰
/teams/{teamId}/projects/{projKey}/gantt        # Gantt 뷰
/teams/{teamId}/projects/{projKey}/dashboard    # 대시보드
/teams/{teamId}/projects/{projKey}/tasks/{number}  # 업무 상세 (전체 페이지)
/settings                                      # 사용자 설정 (세션 관리 포함)
/admin                                         # 관리자 설정
```

### 13.2 필터 URL 동기화

```
/teams/{teamId}/projects/{projKey}/kanban?status=TODO,PROGRESS&assignee=me&priority=1,2,3&unassigned=true
```

- **nuqs** 라이브러리로 URL query params <-> 상태 양방향 동기화
- 필터된 뷰를 URL 공유/북마크 가능
- 페이지 새로고침 시 필터 유지
- **Unassigned 필터**: `unassigned=true` 토글로 미할당 업무만 필터링

### 13.3 키보드 단축키 (Linear 표준 + 커스터마이즈)

| 단축키 | 동작 |
|--------|------|
| `C` | 업무 생성 |
| `K` 또는 `Cmd+K` | 검색 팔레트 |
| `G` then `B` | Kanban 뷰 이동 |
| `G` then `T` | Table 뷰 이동 |
| `G` then `G` | Gantt 뷰 이동 |
| `J` / `K` | 리스트 위/아래 이동 |
| `Enter` | 선택 업무 열기 (사이드 패널) |
| `?` | 단축키 목록 표시 |

- 설정에서 사용자 커스터마이즈 가능

### 13.4 Optimistic UI 정책

| 동작 | 전략 | 상세 |
|------|------|------|
| Kanban DnD | Optimistic | 즉시 이동, 실패 시 롤백 |
| 코멘트 작성 | Optimistic | 즉시 표시, 실패 시 제거 |
| 업무 생성 | **Optimistic (임시 카드)** | Kanban에 임시 카드 즉시 표시, 서버 확인 후 실제 데이터로 교체. 실패 시 카드 제거 |
| 상태 변경 | Server-first | 서버 응답 후 반영 (blocked_by 검증 필요) |
| 동시 편집 | Last Write Wins | SSE로 다른 사용자 수정 실시간 반영. 충돌 시 토스트: "OOO님이 이 업무를 수정했습니다" |

### 13.5 Kanban 뷰 상세

- **칼럼**: BACKLOG, TODO, PROGRESS, REVIEW, DONE, REOPEN, CLOSED
- **Unassigned 필터**: 상단 필터 토글로 미할당 업무만 표시/전체 표시 전환 (별도 칼럼 아님)
- **Blocked 표시**: 카드에 빨간 자물쇠 배지
- **드롭 차단**: PROGRESS 칼럼에 드롭할 때만 blocked_by 검증. 위반 시 차단 + 툴팁으로 사유 표시
- **드래그**: 드래그 자체는 허용 (다른 칼럼 이동은 자유)

### 13.6 업무 상세 뷰

- **사이드 패널 방식** (Linear 스타일): Kanban/Table 위에 오른쪽 슬라이드 패널로 업무 상세 표시
- 목록을 보면서 동시에 상세 확인 가능 (컨텍스트 유지)
- URL: `/teams/{teamId}/projects/{projKey}/tasks/{number}` (전체 페이지로도 접근 가능)

### 13.7 이미지 붙여넣기

- 에디터(tiptap)에서 이미지 paste 시 **즉시 `/attachments/upload`로 업로드**
- 업로드 완료 후 에디터에 이미지 URL 삽입
- **임시 저장**: `attachments.is_temp = TRUE`로 마킹
- 업무 저장 시 `is_temp = FALSE`로 전환
- **24시간 TTL**: cron으로 `is_temp = TRUE`이고 24시간 경과한 파일 자동 삭제

### 13.8 UI/UX 기본

| 항목 | 결정 |
|------|------|
| 디자인 스타일 | Linear 스타일 (다크 테마 기본, 미니멀, 키보드 중심) |
| CSS 프레임워크 | **Tailwind CSS v4** (다크 모드 네이티브 지원) |
| 아이콘 | Fluent UI System Icons |
| Markdown 에디터 | **tiptap** (WYSIWYG + @멘션 플러그인) |
| 차트 | **recharts** (React 선언적 API) |
| 라우팅 | **React Router v7** |
| 모바일 | 반응형 웹 |
| 다국어 | 한/영 지원 (i18next) |
| Gantt 의존성 | 화살표로 시각적 표시 (frappe-gantt) |
| 로그인 UI | **미니멀 중앙 카드** (Google 버튼 + 구분선 + 이메일/비밀번호) |
| 기본 뷰 | **마지막 사용 뷰 localStorage 기억** (없으면 Kanban) |

### 13.9 사이드바 네비게이션 (Linear 스타일)

- **팀 전환**: 상단 드롭다운으로 팀 선택/전환
- **즐겨찾기**: 핀 고정된 프로젝트 목록 (빠른 접근)
- **My Issues**: 현재 사용자에게 할당된 모든 업무 (팀/프로젝트 횡단)
- **프로젝트 목록**: 선택된 팀의 활성 프로젝트 (아카이브 숨김)
- **접기/펼치기**: 사이드바 토글 가능

### 13.10 온보딩 마법사

최초 로그인 시 3단계 마법사 (각 단계 건너뛰기 가능):

1. **프로필 설정**: 이름, 아바타, 타임존, 언어
2. **팀 참여**: 팀 생성 또는 초대 링크/코드로 기존 팀 참여
3. **프로젝트 참여**: 새 프로젝트 생성 또는 기존 프로젝트 선택

- 건너뛰기 시 빈 대시보드 + '팀 만들기' CTA 표시
- 온보딩 완료 여부: `users.onboarding_completed`
- 마법사 다시 보지 않기 옵션

---

## 14. FastMCP 통합

### 방식
FastAPI 앱에 MCP 서버를 마운트하여 단일 프로세스 운영.
services 계층 공유로 API와 동일한 비즈니스 로직 사용.

### MCP 인증
- **사용자별 API Key** (`user_api_keys` 테이블)
- API Key로 사용자 식별 -> 해당 사용자 권한으로 동작
- MCP 작업도 `audit_logs`에 기록 (`source='mcp'`)
- MCP 변경도 **SSE 이벤트 발행** (services 계층 공유이므로 자동)

### MCP Tool 목록 (~14개)

1. `list_projects` - 프로젝트 목록 조회
2. `get_project` - 프로젝트 상세 조회
3. `list_tasks` - 업무 목록 (필터: 상태, 담당자, 긴급도, 태그)
4. `get_task` - 업무 상세 조회
5. `create_task` - 업무 생성
6. `update_task` - 업무 수정
7. `change_task_status` - 업무 상태 변경
8. `add_comment` - 코멘트 추가
9. `search_tasks` - Full-text 검색
10. `get_dashboard` - 프로젝트 대시보드 요약
11. `get_my_tasks` - 현재 사용자의 담당 업무
12. `add_blocked_by` - 의존성 추가
13. `list_tags` - 태그 목록
14. `get_tasks_by_tag` - 태그별 업무

---

## 15. Alert 시스템 아키텍처

### Strategy 패턴

```
AlertChannel (ABC)
├── SmtpEmailChannel
├── ApiEmailChannel (SendGrid/Mailgun)
├── TelegramChannel
├── DiscordChannel
├── GoogleChatChannel
└── SlackChannel

AlertDispatcher
├── 수신자 결정 (생성자, 담당자, Watcher, @멘션 대상)
├── min_alert_priority 필터
├── DND 시간대 체크
├── alert_logs에 pending 저장 (디제스트용)
└── APScheduler 5분 배치 전송
```

### 디제스트 구현 (DB 기반)
1. 알림 이벤트 발생 시 `alert_logs`에 `status='pending'`으로 저장
2. APScheduler가 5분마다 pending 건을 `user_id + task_id` 기준 그룹핑
3. 동일 업무에 대한 여러 알림을 1개 디제스트로 합산 전송
4. 전송 완료 후 `status='sent'` 업데이트
5. 실패 시 3회 재시도 (지수 백오프) 후 `status='failed'`

### Email 백엔드 전환
- `system_settings.email_backend` 값에 따라 SMTP/API 자동 선택
- SMTP: `aiosmtplib`, API: `httpx`

### Alert 트리거
| 이벤트 | 수신자 | 채널 |
|--------|--------|------|
| 업무 생성 | 담당자, CC | 전체 활성 채널 |
| 상태 변경 | 생성자, 담당자, Watcher | 전체 활성 채널 |
| 코멘트 추가 | 생성자, 담당자, Watcher | 전체 활성 채널 |
| @멘션 | 멘션된 사용자 | 전체 활성 채널 |
| 일일 요약 | 팀원 전원 | Email 전용 |

### DND (방해금지 모드)
- `users.dnd_start` ~ `dnd_end` 시간대에는 실시간 알림 차단
- 일일 요약 메일은 DND와 무관하게 발송
- DND 중 수신 알림은 디제스트에 포함 -> DND 해제 후 배치 전송
- 프론트엔드: 프로필 > 알림 설정 > DND 시간대 토글

### RSS Feed
- `task_history` 기반 동적 XML 생성 (별도 테이블 불필요)
- 프로젝트별 `/projects/{id}/rss` 엔드포인트

### 일일 요약 스케줄러
- APScheduler + PostgreSQL advisory lock (멀티 인스턴스 중복 방지)
- 시스템 timezone 기준 실행 (기본 UTC 00:00)
- 분류: 새로 생성, 마감 임박(D-3), 일정 미설정, 오늘 마감, Blocked 업무

---

## 16. Google Calendar 연동

### 전략: 프로젝트별 전용 캘린더, 단방향 동기화 (Jongji -> GCal)
- 프로젝트장/팀장이 GCal 연동 -> 전용 캘린더 자동 생성
- 업무 생성/수정/삭제(Archive) 시 GCal 이벤트 자동 동기화

### 이벤트 형식
- 제목: `[담당자이름] 업무제목`
- 기간: start_date ~ due_date (all-day event)
- 설명: 업무 상세정보 요약 + Jongji 링크

### OAuth Scope
- `https://www.googleapis.com/auth/calendar`
- 토큰 암호화 저장 (`google_calendar_configs`)

---

## 17. 파일 저장소 설계

### 추상화 계층

```
StorageBackend (ABC)
├── LocalStorage (Docker 볼륨 마운트)
└── S3Storage (boto3, MinIO 호환)

설정: system_settings.storage_backend = 'local' | 's3'
```

### 제한사항
- 최대 파일 크기: 50MB (설정 가능)
- 허용 MIME 타입: 이미지, PDF, 문서, 압축 파일 등 화이트리스트

---

## 18. 운영/인프라

### 18.1 모니터링
- `GET /health` - Docker healthcheck 연동 (DB 연결, 디스크 공간)
- `GET /ready` - 서비스 준비 상태 (마이그레이션 완료 등)
- loguru JSON 구조화 로깅

### 18.2 데이터 보존 정책
| 테이블 | 파티셔닝 | 보존 |
|--------|----------|------|
| audit_logs | 월별 | **90일 TTL** (cron 삭제) |
| task_history | 월별 | **영구 보존** |
| alert_logs | - | 90일 TTL |

### 18.3 스케줄러
- APScheduler + **PostgreSQL advisory lock** (멀티 인스턴스 중복 실행 방지)

### 18.4 개발 환경
- **전체 Docker Compose** (backend, frontend, PostgreSQL 모두 Docker)
- `docker-compose.dev.yml`로 볼륨 마운트 + hot-reload
- Backend: `uvicorn --reload` (Docker 내부)
- Frontend: `vite dev` (Docker 내부)

### 18.5 테스트 환경
- **testcontainers-python**으로 실제 PostgreSQL 컨테이너 사용
- PG 전용 기능(tsvector, ENUM, LISTEN/NOTIFY) 완전 테스트 가능
- 각 테스트 트랜잭션 롤백으로 격리

### 18.6 백업
- Docker 볼륨 + `pg_dump` 자동 스크립트 (`scripts/backup.sh`)

### 18.7 성능 목표

| 지표 | 목표값 | 측정 방법 |
|------|--------|----------|
| API 응답 (p95) | < 500ms | 미들웨어 로깅 |
| Kanban 뷰 초기 로딩 | < 2초 | Performance API |
| 동시 접속 사용자 | 50명 | SSE 연결 기준 |
| DB 쿼리 단건 | < 100ms | SQLAlchemy 이벤트 로깅 |
| SSE 이벤트 전파 지연 | < 1초 | LISTEN/NOTIFY -> 클라이언트 |

### 18.8 에러 복구 전략

| 대상 | 전략 | 상세 |
|------|------|------|
| GCal 동기화 실패 | 재시도 3회 (지수 백오프: 1s->4s->16s) | alert_logs 기록 |
| Alert 전송 실패 | 재시도 3회 (지수 백오프) | retry_count, error_message 기록 |
| SSE 연결 끊김 | Last-Event-Id 기반 재연결 | 버퍼 100건/프로젝트, 5분 TTL. 초과 시 TanStack Query refetch |
| 수동 복구 | Admin 대시보드 '재동기화' 버튼 | GCal 전체 재동기화, 실패 알림 재전송 |

---

## 19. 의존성 제한

| 제한 | 값 | 사유 |
|------|-----|------|
| 직접 blocked_by 수 | **최대 10개** | 실무에 충분한 범위 |
| 전체 체인 깊이 | **최대 20** | DFS 탐색 비용 제한 |
| 순환 검증 | DFS 기반 | 의존성 추가 시 필수 |

---

## 20. 대시보드

- **실시간 SQL 집계** (API 호출 시 계산)
- **TanStack Query staleTime 5분** (프론트엔드 캐시)
- 차트: 번다운, 상태 분포, 추세선 등 (**recharts**)
- Materialized View 불필요 (초기에 충분한 성능)

---

## 21. 구현 Phase (7단계)

### Phase 1: Foundation (기반)
1. 프로젝트 초기화 (backend: uv + FastAPI, frontend: Vite + React + Tailwind CSS v4 + i18next)
2. Docker Compose 설정 (PostgreSQL, backend, frontend) + dev 환경
3. SQLAlchemy 모델 전체 (23개 테이블) + Alembic 마이그레이션
4. `system_settings` 테이블 + config 관리 (`setup_completed`, `app_name`, `default_locale` 포함)
5. Auth 구현 (Google OAuth + 자체가입 + JWT + refresh_tokens + CSRF + 비밀번호 8자 검증)
6. **Setup Wizard API** (`/setup/status`, `/setup/admin`, `/setup/settings`, `/setup/complete`) + Race Condition 방지 + 기본 라벨 seed
7. User CRUD API (+ timezone, API Key 관리, 세션 관리 API, 계정 비활성화 + **마지막 Admin 탈퇴 차단**)
8. CLAUDE.md 작성

### Phase 2a: Core Backend - 팀/프로젝트
1. Team CRUD API + 역할/권한 + 직접 멤버 추가 + **팀 아카이브 캐스케이드**
2. Project CRUD API + 라벨 CRUD + **key 영구 점유 정책**
3. 기본 Task CRUD API + **담당자 프로젝트 멤버 검증**
4. 팀 초대 링크 API (team_invites CRUD + join)

### Phase 2b: Core Backend - 업무 핵심
1. Task 상태 전이 (선언적 전이 테이블 기반, blocked_by DAG 검증)
2. #태그 자동 추출 + 태그 API
3. Comment + History API + **@멘션 파싱 + Watcher 자동 등록 + 알림**
4. SSE 실시간 업데이트 (PG LISTEN/NOTIFY 기반 EventBus)
5. 업무 복제 API + 템플릿 CRUD API

### Phase 2c: Core Frontend
1. Layout (Linear 스타일 다크 테마, Fluent UI Icons, **Tailwind CSS v4**, **사이드바 네비게이션**)
2. **로그인 페이지** (미니멀 중앙 카드)
3. **Setup Wizard UI** (중앙 카드 + Stepper 3단계, OAuth 환경변수 감지 버튼 토글)
4. Kanban 뷰 (@dnd-kit, Blocked 배지 + 드롭 차단 + **Unassigned 필터 토글**)
4. **업무 상세 사이드 패널** (Linear 스타일)
5. Table 뷰
6. URL 구조 (**React Router v7**) + nuqs 필터 동기화
7. 온보딩 마법사 (3단계 + 건너뛰기)
8. **기본 뷰 localStorage 기억**

### Phase 3: Alert + 검색
1. Full-text Search (tsvector + **pg_trgm 주력** + 코멘트 별도 인덱스)
2. Alert Channel ABC + EmailChannel (SMTP + API 전환)
3. AlertDispatcher + 이벤트 트리거 + **alert_logs DB 기반 디제스트** + 비동기 3회 재시도
4. Telegram/Discord/Slack/GoogleChat 채널
5. RSS Feed 엔드포인트
6. APScheduler + 일일 요약 메일 + advisory lock
7. Frontend: 검색 UI + 검색 팔레트 (Cmd+K)
8. Frontend: 프로필 설정에 DND 시간대 UI

### Phase 4: 첨부 + MCP + Export
1. 파일 저장소 추상화 (Local + S3)
2. 첨부 파일 API + 임시 업로드 (24h TTL cron)
3. FastMCP 서버 마운트 + 14개 Tool + 사용자별 API Key
4. Export API (JSON/Markdown)
5. Frontend: 리치 에디터 (**tiptap**) + 이미지 paste 자동 업로드 + **@멘션 자동완성**
6. Frontend: 첨부 파일 UI

### Phase 5: Calendar + Gantt + Dashboard
1. Google Calendar OAuth 프로젝트별 연동
2. 이벤트 자동 동기화 로직
3. Frontend: Dashboard (**recharts**, 번다운, 상태 분포 - 실시간 SQL + 5분 캐시)
4. Frontend: Gantt Chart (frappe-gantt, 의존성 화살표, 드래그 일정 조정)

### Phase 6: Polish + 보안
1. Passkey/2FA 선택적 지원
2. 감사 로그 (레벨별 저장 + Admin 조회 + 월별 파티셔닝 + 90일 TTL)
3. 키보드 단축키 (Linear 표준 + 커스터마이즈)
4. Frontend: 반응형 레이아웃, 라이트/다크 모드 전환
5. Frontend: 한/영 전환
6. Frontend: **세션 관리 UI** (활성 세션 목록 + 로그아웃)
7. /health, /ready 헬스체크
8. 백업 스크립트 (pg_dump)
9. E2E 테스트
10. 배포 문서

### Phase 7: MCP CLI Client
1. MCP Python SDK Client 기반 CLI 구현
2. 14개 MCP Tool 전체를 서브커맨드로 매핑
3. JSON 출력 기본 (자동화/스크립트 친화적)
4. API Key 인증 (환경변수 `JONGJI_API_KEY` 또는 `~/.jongji/config.toml`)
5. backend `pyproject.toml`에 `[project.scripts]` 엔트리포인트 등록

---

## 22. MCP CLI Client

### 개요
Jongji MCP Server의 14개 Tool을 터미널에서 직접 호출할 수 있는 CLI 클라이언트.
MCP Python SDK의 Client를 사용하여 MCP 네이티브 프로토콜로 통신.

### 기술 스택
- **MCP Python SDK** (`mcp` 패키지의 Client 클래스)
- JSON 출력 기본
- backend `pyproject.toml`의 `[project.scripts]`로 `jongji` 커맨드 등록

### 인증
- 환경변수: `JONGJI_API_KEY`
- 설정 파일: `~/.jongji/config.toml`
```toml
[auth]
api_key = "jk_xxxxxxxxxxxxxxxx"
server_url = "http://localhost:8000"
```

### CLI 커맨드 구조

```
jongji <command> [options]
```

| 커맨드 | MCP Tool | 설명 |
|--------|----------|------|
| `jongji projects list` | list_projects | 프로젝트 목록 |
| `jongji projects get <id>` | get_project | 프로젝트 상세 |
| `jongji tasks list --project=<id>` | list_tasks | 업무 목록 (필터 지원) |
| `jongji tasks get <id>` | get_task | 업무 상세 |
| `jongji tasks create --project=<id> --title=<t>` | create_task | 업무 생성 |
| `jongji tasks update <id> --title=<t>` | update_task | 업무 수정 |
| `jongji tasks status <id> <status>` | change_task_status | 상태 변경 |
| `jongji tasks comment <id> --content=<c>` | add_comment | 코멘트 추가 |
| `jongji search --query=<q>` | search_tasks | 검색 |
| `jongji dashboard <project_id>` | get_dashboard | 대시보드 요약 |
| `jongji my-tasks` | get_my_tasks | 내 담당 업무 |
| `jongji tasks block <id> --by=<id>` | add_blocked_by | 의존성 추가 |
| `jongji tags list --project=<id>` | list_tags | 태그 목록 |
| `jongji tags tasks <tag>` | get_tasks_by_tag | 태그별 업무 |

### 출력 형식
- 기본: JSON (stdout)
- `--format=table` 옵션으로 테이블 출력 (선택적)
- 파이프라인 친화적: `jongji tasks list | jq '.[] | .title'`

### 패키지 구조
```
backend/src/jongji/
└── cli/
    ├── __init__.py
    ├── main.py          # CLI 엔트리포인트
    ├── client.py        # MCP SDK Client 래퍼
    └── commands/
        ├── __init__.py
        ├── projects.py
        ├── tasks.py
        ├── search.py
        ├── dashboard.py
        └── tags.py
```

### pyproject.toml 설정
```toml
[project.scripts]
jongji = "jongji.cli.main:app"
```

---

## 23. 보안 고려사항

- OAuth 토큰 / 웹훅 URL 암호화 저장 (Fernet)
- 비밀번호 해싱 (bcrypt), 최소 8자 검증
- Refresh Token: HttpOnly 쿠키 + CSRF Double Submit Cookie
- 로그인 보안: Rate limit + progressive delay + 계정 잠금
- API Rate Limiting (slowapi: 100req/min 기본, 로그인 10req/min)
- CORS 설정 (프론트엔드 도메인만)
- 교차 팀/프로젝트 접근 차단 (미들웨어)
- XSS 방지 (Markdown 렌더링 시 DOMPurify sanitize)
- 파일 업로드 MIME 타입 검증 + 크기 제한
- MCP: 사용자별 API Key (단일 키 공유 금지)
- 감사 로그: source 필드로 API/MCP 구분
- 초대 링크: 토큰 만료 + 최대 사용 횟수 제한
- 선택적 Passkey/2FA (Phase 6)
- 다중 세션 관리: 사용자가 직접 세션 확인/해제 가능

---

## 24. 검증 방법

1. `pytest` + **testcontainers-python** - Backend 단위/통합 테스트 (실제 PG 컨테이너)
2. `ruff check` + `ty` - 린트/타입 검사
3. Docker Compose로 전체 서비스 기동 테스트
4. API 문서: FastAPI `/docs` (Swagger UI)
5. MCP 연동: Claude Desktop에서 MCP 서버 연결 테스트
6. SSE: 다중 브라우저 탭에서 실시간 반영 테스트
7. Full-text Search: 한국어/영어 검색 결과 확인 (pg_trgm 주력 + tsvector 보조)
8. Kanban DnD: Blocked 업무 드롭 차단 동작 확인
9. 키보드 단축키: 모든 단축키 동작 확인
10. Rate Limiting: 로그인 brute force 테스트
11. CSRF: Refresh Token 갱신 시 CSRF 토큰 검증 확인
12. 성능: API p95 < 500ms, Kanban < 2s 로딩 확인
13. 초대 링크: 만료/최대 사용 횟수 동작 확인
14. DND: 방해금지 시간대 알림 차단 확인
15. 알림 디제스트: DB 기반 배치 전송 동작 확인
16. 세션 관리: 다중 로그인 + 세션 로그아웃 동작 확인
17. 팀 아카이브: 캐스케이드 동작 확인
18. @멘션: Watcher 자동 등록 + 알림 동작 확인

---

## 25. 인터뷰 3차 결정사항 요약

| # | 항목 | 결정 |
|---|------|------|
| 1 | SSE 재연결 (5분 초과) | TanStack Query refetch 위임 |
| 2 | 알림 디제스트 구현 | DB 기반 (alert_logs pending -> APScheduler 5분 배치) |
| 3 | 아카이브 Project Key | 영구 점유 (재사용 불가) |
| 4 | Kanban Unassigned | 필터 토글 방식 (별도 칼럼 아님) |
| 5 | 비밀번호 정책 | 최소 8자 (길이만 검증) |
| 6 | 세션 관리 | 다중 로그인 + 세션 관리 UI |
| 7 | 팀 아카이브 | 확인 후 캐스케이드 |
| 8 | MD 에디터 | tiptap 확정 |
| 9 | 차트 라이브러리 | recharts 확정 |
| 10 | 계정 탈퇴 | 소프트 비활성화 |
| 11 | 한국어 검색 | pg_trgm 주력 + tsvector 보조 |
| 12 | 업무 상세 UI | 사이드 패널 (Linear 스타일) |
| 13 | @멘션 | Phase 2b (Watcher 자동 등록 + 알림) |
| 14 | Time Tracking | 초기 불필요 |
| 15 | 사이드바 | Linear 스타일 (팀 전환 + 즐겨찾기) |
| 16 | 테스트 DB | testcontainers-python (실제 PG) |
| 17 | 담당자 정책 | 선택적, 프로젝트 멤버만 |
| 18 | 라우팅 | React Router v7 |
| 19 | 로그인 UI | 미니멀 중앙 카드 |
| 20 | CSS | Tailwind CSS v4 |
| 21 | 개발 환경 | 전체 Docker |
| 22 | 다중 담당자 | 불필요 (단일만) |
| 23 | 기본 뷰 | 마지막 사용 뷰 localStorage 기억 |
| 24 | MCP Client 용도 | Jongji MCP Server용 CLI 클라이언트 |
| 25 | MCP Client 구현 시점 | Phase 7 (별도 Phase) |
| 26 | MCP Client 기술 | MCP Python SDK Client + JSON 출력 + backend 엔트리포인트 |
