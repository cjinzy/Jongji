#!/usr/bin/env bash
# setup.sh — Jongji 초기 설정 스크립트.
#
# 프로젝트 루트에서 실행:
#   bash setup.sh
#
# 기능:
#   - .env.example → .env 복사 (POSTGRES_PASSWORD, SECRET_KEY, SETUP_TOKEN 자동 생성)
#   - Docker Compose 실행
#   - 초기 Admin 계정 자동 생성 (POST /api/v1/setup/admin)
#   - Setup 완료 처리 (POST /api/v1/setup/complete)
#   - .credentials 파일에 자격증명 저장
#
# 멱등성:
#   - .env 파일이 이미 있으면 생성 단계를 건너뜁니다.
#   - .credentials 파일이 이미 있으면 admin 생성 단계를 건너뜁니다.

set -euo pipefail

# ── 스크립트 위치 기준으로 프로젝트 루트 결정 ──────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"

ENV_EXAMPLE="${PROJECT_ROOT}/.env.example"
ENV_FILE="${PROJECT_ROOT}/.env"
CREDENTIALS_FILE="${PROJECT_ROOT}/.credentials"

# ── 유틸리티 함수 ──────────────────────────────────────────────────

# 영숫자 랜덤 문자열 생성
generate_password() {
    local length="${1:-32}"
    openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c "$length"
}

# Admin 비밀번호: 대문자+숫자 반드시 포함, 12자
generate_admin_password() {
    while true; do
        local pw
        pw="$(openssl rand -base64 16 | tr -dc 'A-Za-z0-9' | head -c 12)"
        if [[ "$pw" =~ [A-Z] ]] && [[ "$pw" =~ [0-9] ]]; then
            echo "$pw"
            return
        fi
    done
}

# Backend health check 대기 (최대 60초)
wait_for_backend() {
    local max_attempts=30
    local attempt=0
    echo "Backend 준비 대기 중..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:8888/api/v1/setup/status > /dev/null 2>&1; then
            echo "Backend 준비 완료."
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "오류: Backend가 60초 내에 응답하지 않습니다." >&2
    return 1
}

# ── 사전 조건 확인 ─────────────────────────────────────────────────
if [[ ! -f "${ENV_EXAMPLE}" ]]; then
    echo "오류: .env.example 파일을 찾을 수 없습니다: ${ENV_EXAMPLE}" >&2
    exit 1
fi

if ! command -v openssl &>/dev/null; then
    echo "오류: openssl 명령을 찾을 수 없습니다. openssl을 설치하세요." >&2
    exit 1
fi

if ! command -v curl &>/dev/null; then
    echo "오류: curl 명령을 찾을 수 없습니다. curl을 설치하세요." >&2
    exit 1
fi

if ! command -v docker &>/dev/null; then
    echo "오류: docker 명령을 찾을 수 없습니다. docker를 설치하세요." >&2
    exit 1
fi

# ══════════════════════════════════════════════════════════════════
# Step 1: .env 파일 생성
# ══════════════════════════════════════════════════════════════════
if [[ -f "${ENV_FILE}" ]]; then
    echo "ℹ  .env 파일이 이미 존재합니다. 생성 단계를 건너뜁니다."
    echo "   (재생성하려면 .env 파일을 삭제 후 다시 실행하세요)"
else
    echo "── .env 파일 생성 ──────────────────────────────────────"

    # 무작위 값 생성
    POSTGRES_PASSWORD="$(generate_password 32)"
    SECRET_KEY="$(openssl rand -hex 32)"
    SETUP_TOKEN="$(generate_password 32)"

    # .env.example → .env 복사
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"

    # 값 치환
    sed -i'' "s/CHANGE_ME_STRONG_PASSWORD/${POSTGRES_PASSWORD}/g" "${ENV_FILE}"
    sed -i'' "s/CHANGE_ME_RANDOM_SECRET_KEY/${SECRET_KEY}/" "${ENV_FILE}"
    sed -i'' "s/CHANGE_ME_SETUP_TOKEN/${SETUP_TOKEN}/" "${ENV_FILE}"

    # 파일 권한 설정
    chmod 600 "${ENV_FILE}"

    echo "완료: .env 파일이 생성되었습니다."
    echo "  위치: ${ENV_FILE}"
    echo "  권한: 600 (소유자만 읽기/쓰기)"
fi

# ══════════════════════════════════════════════════════════════════
# Step 2: Docker Compose 실행 및 Admin 계정 생성
# ══════════════════════════════════════════════════════════════════
if [[ -f "${CREDENTIALS_FILE}" ]]; then
    echo ""
    echo "ℹ  .credentials 파일이 이미 존재합니다. Admin 생성 단계를 건너뜁니다."
    echo "   (재생성하려면 .credentials 파일을 삭제 후 다시 실행하세요)"
    echo ""
    echo "기존 자격증명:"
    cat "${CREDENTIALS_FILE}"
    exit 0
fi

# .env에서 값 읽기 (Step 1에서 생성했거나 기존 파일)
SETUP_TOKEN="$(grep '^SETUP_TOKEN=' "${ENV_FILE}" | cut -d'=' -f2-)"
POSTGRES_PASSWORD="$(grep '^POSTGRES_PASSWORD=' "${ENV_FILE}" | cut -d'=' -f2-)"

if [[ -z "${SETUP_TOKEN}" ]]; then
    echo "오류: .env 파일에 SETUP_TOKEN이 설정되지 않았습니다." >&2
    exit 1
fi

# Admin 비밀번호 생성
ADMIN_PASSWORD="$(generate_admin_password)"

echo ""
echo "── Docker Compose 실행 ─────────────────────────────────"
cd "${PROJECT_ROOT}"
docker compose up -d --build

# Backend 준비 대기
if ! wait_for_backend; then
    echo "오류: Backend 시작에 실패했습니다. 'docker compose logs backend'를 확인하세요." >&2
    exit 1
fi

echo ""
echo "── Admin 계정 생성 ─────────────────────────────────────"

# POST /api/v1/setup/admin
ADMIN_RESPONSE=$(curl -sf -w "\n%{http_code}" -X POST http://localhost:8888/api/v1/setup/admin \
    -H "Authorization: Bearer ${SETUP_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"admin@jongji.app\",\"password\":\"${ADMIN_PASSWORD}\",\"name\":\"administrator\"}")

ADMIN_HTTP_CODE=$(echo "$ADMIN_RESPONSE" | tail -1)
ADMIN_BODY=$(echo "$ADMIN_RESPONSE" | sed '$d')

if [[ "$ADMIN_HTTP_CODE" -ge 200 && "$ADMIN_HTTP_CODE" -lt 300 ]]; then
    echo "Admin 계정 생성 완료."
else
    echo "오류: Admin 계정 생성 실패 (HTTP ${ADMIN_HTTP_CODE})" >&2
    echo "응답: ${ADMIN_BODY}" >&2
    exit 1
fi

# POST /api/v1/setup/complete
COMPLETE_RESPONSE=$(curl -sf -w "\n%{http_code}" -X POST http://localhost:8888/api/v1/setup/complete \
    -H "Authorization: Bearer ${SETUP_TOKEN}")

COMPLETE_HTTP_CODE=$(echo "$COMPLETE_RESPONSE" | tail -1)

if [[ "$COMPLETE_HTTP_CODE" -ge 200 && "$COMPLETE_HTTP_CODE" -lt 300 ]]; then
    echo "Setup 완료 처리 성공."
else
    echo "경고: Setup 완료 처리 실패 (HTTP ${COMPLETE_HTTP_CODE}). Admin 계정은 생성되었습니다." >&2
fi

# ══════════════════════════════════════════════════════════════════
# Step 3: .credentials 파일 저장 및 출력
# ══════════════════════════════════════════════════════════════════
GENERATED_DATE="$(date +%Y-%m-%d)"

cat > "${CREDENTIALS_FILE}" <<CRED
========================================
  Jongji Setup Credentials
  Generated: ${GENERATED_DATE}
========================================

[PostgreSQL]
  User:     jongji
  Password: ${POSTGRES_PASSWORD}

[Admin Account]
  Email:    admin@jongji.app
  Name:     administrator
  Password: ${ADMIN_PASSWORD}

⚠️  이 파일을 안전한 곳에 보관하세요.
========================================
CRED

chmod 600 "${CREDENTIALS_FILE}"

echo ""
echo "── 자격증명 정보 ───────────────────────────────────────"
cat "${CREDENTIALS_FILE}"
echo ""
echo "자격증명 파일: ${CREDENTIALS_FILE} (권한: 600)"
echo ""
echo "※ GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI는"
echo "  .env 파일을 직접 편집하여 설정하세요."
