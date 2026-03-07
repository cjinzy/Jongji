#!/usr/bin/env bash
# setup.sh — .env 파일 자동 생성 스크립트.
#
# 프로젝트 루트에서 실행:
#   bash scripts/setup.sh
#
# 기능:
#   - .env.example → .env 복사
#   - POSTGRES_PASSWORD 및 DATABASE_URL의 CHANGE_ME_STRONG_PASSWORD를 무작위 비밀번호로 교체
#   - SECRET_KEY의 CHANGE_ME_RANDOM_SECRET_KEY를 무작위 hex 키로 교체
#   - .env 파일 권한을 600으로 설정

set -euo pipefail

# 스크립트 위치 기준으로 프로젝트 루트 결정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ENV_EXAMPLE="${PROJECT_ROOT}/.env.example"
ENV_FILE="${PROJECT_ROOT}/.env"

# ── 사전 조건 확인 ────────────────────────────────────────────────
if [[ ! -f "${ENV_EXAMPLE}" ]]; then
    echo "오류: .env.example 파일을 찾을 수 없습니다: ${ENV_EXAMPLE}" >&2
    exit 1
fi

if ! command -v openssl &>/dev/null; then
    echo "오류: openssl 명령을 찾을 수 없습니다. openssl을 설치하세요." >&2
    exit 1
fi

# ── 기존 .env 파일 처리 ───────────────────────────────────────────
if [[ -f "${ENV_FILE}" ]]; then
    echo "경고: .env 파일이 이미 존재합니다."
    read -r -p "덮어쓰시겠습니까? [y/N] " answer
    case "${answer}" in
        [Yy]*) ;;
        *)
            echo "중단: 기존 .env 파일을 유지합니다."
            exit 0
            ;;
    esac
fi

# ── .env.example 복사 ─────────────────────────────────────────────
cp "${ENV_EXAMPLE}" "${ENV_FILE}"
echo ".env.example → .env 복사 완료"

# ── 무작위 값 생성 ────────────────────────────────────────────────
# POSTGRES_PASSWORD: 영문+숫자 32자리
POSTGRES_PASSWORD="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)"

# SECRET_KEY: hex 64자리 (256비트)
SECRET_KEY="$(openssl rand -hex 32)"

# ── 값 치환 (macOS/Linux 호환: sed -i'') ─────────────────────────
# POSTGRES_PASSWORD 행 치환
sed -i'' "s/CHANGE_ME_STRONG_PASSWORD/${POSTGRES_PASSWORD}/g" "${ENV_FILE}"

# SECRET_KEY 행 치환
sed -i'' "s/CHANGE_ME_RANDOM_SECRET_KEY/${SECRET_KEY}/" "${ENV_FILE}"

# ── 파일 권한 설정 ────────────────────────────────────────────────
chmod 600 "${ENV_FILE}"

echo ""
echo "완료: .env 파일이 생성되었습니다."
echo "  위치: ${ENV_FILE}"
echo "  권한: 600 (소유자만 읽기/쓰기)"
echo ""
echo "※ GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI는"
echo "  직접 편집하여 설정하세요."
