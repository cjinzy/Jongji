# Phase 1: Foundation - 구현 계획

> **상태**: IN PROGRESS
> **방법론**: Ralph (지속 루프) + Team (병렬 에이전트) + TDD (테스트 우선)

---

## 작업 분해 (6개 병렬 트랙)

### Track 1: Backend 프로젝트 초기화 [worker-1]
- `backend/pyproject.toml` (uv, FastAPI, SQLAlchemy, Alembic, pydantic-settings, loguru, slowapi 등)
- `backend/src/jongji/__init__.py`
- `backend/src/jongji/config.py` (pydantic-settings 기반 Settings)
- `backend/src/jongji/database.py` (async engine, session)
- `backend/src/jongji/main.py` (FastAPI app 골격)
- ruff, ty 설정

### Track 2: Frontend 프로젝트 초기화 [worker-2]
- Vite + React 19 + TypeScript 프로젝트 생성
- Tailwind CSS v4 설정
- i18next + react-i18next 설정 (ko.json, en.json 기본)
- React Router v7 기본 라우팅
- Zustand + TanStack Query 설정
- @fluentui/react-icons 설치

### Track 3: 인프라 (Docker) [worker-3]
- `docker-compose.yml` (PostgreSQL)
- `docker-compose.dev.yml` (backend + frontend + PG, hot-reload)
- `Dockerfile.backend`
- `Dockerfile.frontend`
- `scripts/backup.sh`

### Track 4: SQLAlchemy 모델 (23개 테이블) [worker-4]
**의존성**: Track 1 완료 후
- 모든 모델 파일 (user, team, project, task, label, attachment, alert, audit)
- Alembic 초기 마이그레이션
- ENUM 타입 정의
- 인덱스 전략 적용
- **TDD**: 모델 테스트 (conftest.py + testcontainers)

### Track 5: Auth 시스템 + Setup Wizard [worker-5]
**의존성**: Track 4 완료 후
- auth_service.py (Google OAuth + 자체가입 + JWT + refresh_tokens)
- schemas/user.py, schemas/common.py
- api/auth.py (로그인, 회원가입, refresh, OAuth)
- api/deps.py (인증 의존성)
- Setup Wizard API (/setup/status, /setup/admin, /setup/settings, /setup/complete)
- Rate limiting (slowapi)
- CSRF Double Submit Cookie
- **TDD**: test_auth.py

### Track 6: User CRUD API [worker-6]
**의존성**: Track 4 완료 후
- api/users.py
- schemas/user.py (확장)
- 세션 관리 API
- API Key 관리
- 계정 비활성화
- **TDD**: test_users.py (추후 별도 파일)

---

## TDD 전략

각 트랙에서:
1. **RED**: 실패하는 테스트 먼저 작성
2. **GREEN**: 테스트를 통과하는 최소한의 코드 작성
3. **REFACTOR**: 코드 정리 (테스트는 계속 통과)

테스트 환경:
- `testcontainers-python`으로 실제 PostgreSQL 컨테이너 사용
- `conftest.py`에서 DB 세션 fixture 제공
- 각 테스트는 트랜잭션 롤백으로 격리

---

## 완료 기준

- [ ] Backend FastAPI 서버 정상 기동
- [ ] Frontend Vite dev 서버 정상 기동
- [ ] Docker Compose로 전체 스택 기동 가능
- [ ] 23개 테이블 모델 정의 + Alembic 마이그레이션
- [ ] Auth API 동작 (회원가입, 로그인, JWT 갱신)
- [ ] Setup Wizard API 동작
- [ ] User CRUD API 동작
- [ ] 모든 테스트 통과
- [ ] ruff check + ty 통과
