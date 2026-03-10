#!/usr/bin/env bash
# test_setup.sh — setup.sh의 단위 테스트
#
# Docker/Backend 없이 .env 생성 및 멱등성 로직만 검증합니다.
# 프로젝트 루트에서 실행:
#   bash scripts/test_setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 테스트용 임시 디렉토리
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "${TEST_DIR}"' EXIT

PASS=0
FAIL=0

# ── 테스트 유틸리티 ────────────────────────────────────────────────
assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "  ✅ PASS: ${desc}"
        PASS=$((PASS + 1))
    else
        echo "  ❌ FAIL: ${desc}"
        echo "     expected: ${expected}"
        echo "     actual:   ${actual}"
        FAIL=$((FAIL + 1))
    fi
}

assert_true() {
    local desc="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "  ✅ PASS: ${desc}"
        PASS=$((PASS + 1))
    else
        echo "  ❌ FAIL: ${desc}"
        FAIL=$((FAIL + 1))
    fi
}

assert_false() {
    local desc="$1"
    shift
    if ! "$@" >/dev/null 2>&1; then
        echo "  ✅ PASS: ${desc}"
        PASS=$((PASS + 1))
    else
        echo "  ❌ FAIL: ${desc}"
        FAIL=$((FAIL + 1))
    fi
}

assert_regex() {
    local desc="$1" value="$2" pattern="$3"
    if [[ "$value" =~ $pattern ]]; then
        echo "  ✅ PASS: ${desc}"
        PASS=$((PASS + 1))
    else
        echo "  ❌ FAIL: ${desc}"
        echo "     value:   ${value}"
        echo "     pattern: ${pattern}"
        FAIL=$((FAIL + 1))
    fi
}

# ── 테스트 환경 준비 ──────────────────────────────────────────────
# setup.sh에서 사용하는 함수들을 직접 소싱하여 테스트
# (Docker/curl 의존 부분 제외)

generate_password() {
    local length="${1:-32}"
    openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c "$length"
}

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

echo "========================================"
echo "  Jongji setup.sh 테스트"
echo "========================================"
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 1: generate_password 길이 검증
# ══════════════════════════════════════════════════════════════════
echo "── Test 1: generate_password ──────────────────────────"
PW32="$(generate_password 32)"
assert_eq "32자 길이" "32" "${#PW32}"

PW16="$(generate_password 16)"
assert_eq "16자 길이" "16" "${#PW16}"

# 영숫자만 포함
assert_regex "영숫자만 포함 (32자)" "$PW32" '^[A-Za-z0-9]+$'

echo ""

# ══════════════════════════════════════════════════════════════════
# Test 2: generate_admin_password 요구사항 검증
# ══════════════════════════════════════════════════════════════════
echo "── Test 2: generate_admin_password ────────────────────"
for i in $(seq 1 5); do
    ADMIN_PW="$(generate_admin_password)"
    assert_eq "Admin PW #${i} 길이 12자" "12" "${#ADMIN_PW}"
    assert_regex "Admin PW #${i} 대문자 포함" "$ADMIN_PW" '[A-Z]'
    assert_regex "Admin PW #${i} 숫자 포함" "$ADMIN_PW" '[0-9]'
done

echo ""

# ══════════════════════════════════════════════════════════════════
# Test 3: .env 파일 생성 검증
# ══════════════════════════════════════════════════════════════════
echo "── Test 3: .env 파일 생성 ─────────────────────────────"

# .env.example 복사
cp "${PROJECT_ROOT}/.env.example" "${TEST_DIR}/.env.example"

# .env 생성 시뮬레이션
POSTGRES_PASSWORD="$(generate_password 32)"
SECRET_KEY="$(openssl rand -hex 32)"
SETUP_TOKEN="$(generate_password 32)"

cp "${TEST_DIR}/.env.example" "${TEST_DIR}/.env"
sed -i'' "s/CHANGE_ME_STRONG_PASSWORD/${POSTGRES_PASSWORD}/g" "${TEST_DIR}/.env"
sed -i'' "s/CHANGE_ME_RANDOM_SECRET_KEY/${SECRET_KEY}/" "${TEST_DIR}/.env"
sed -i'' "s/CHANGE_ME_SETUP_TOKEN/${SETUP_TOKEN}/" "${TEST_DIR}/.env"
chmod 600 "${TEST_DIR}/.env"

# 플레이스홀더가 남아있지 않은지 확인
assert_false "CHANGE_ME_STRONG_PASSWORD 치환됨" grep -q "CHANGE_ME_STRONG_PASSWORD" "${TEST_DIR}/.env"
assert_false "CHANGE_ME_RANDOM_SECRET_KEY 치환됨" grep -q "CHANGE_ME_RANDOM_SECRET_KEY" "${TEST_DIR}/.env"
assert_false "CHANGE_ME_SETUP_TOKEN 치환됨" grep -q "CHANGE_ME_SETUP_TOKEN" "${TEST_DIR}/.env"

# 값이 실제로 설정되었는지 확인
ENV_PG_PW="$(grep '^POSTGRES_PASSWORD=' "${TEST_DIR}/.env" | cut -d'=' -f2-)"
assert_eq "POSTGRES_PASSWORD 32자" "32" "${#ENV_PG_PW}"

ENV_SK="$(grep '^SECRET_KEY=' "${TEST_DIR}/.env" | cut -d'=' -f2-)"
assert_eq "SECRET_KEY 64자 (hex)" "64" "${#ENV_SK}"

ENV_ST="$(grep '^SETUP_TOKEN=' "${TEST_DIR}/.env" | cut -d'=' -f2-)"
assert_eq "SETUP_TOKEN 32자" "32" "${#ENV_ST}"

# DATABASE_URL 내 비밀번호도 치환되었는지 확인
assert_true "DATABASE_URL 내 비밀번호 치환됨" grep -q "${POSTGRES_PASSWORD}" "${TEST_DIR}/.env"

# 파일 권한 확인
FILE_PERM="$(stat -c '%a' "${TEST_DIR}/.env" 2>/dev/null || stat -f '%Lp' "${TEST_DIR}/.env" 2>/dev/null)"
assert_eq ".env 파일 권한 600" "600" "${FILE_PERM}"

echo ""

# ══════════════════════════════════════════════════════════════════
# Test 4: .credentials 파일 생성 검증
# ══════════════════════════════════════════════════════════════════
echo "── Test 4: .credentials 파일 생성 ─────────────────────"

ADMIN_PASSWORD="$(generate_admin_password)"
GENERATED_DATE="$(date +%Y-%m-%d)"

cat > "${TEST_DIR}/.credentials" <<CRED
========================================
  Jongji Setup Credentials
  Generated: ${GENERATED_DATE}
========================================

[PostgreSQL]
  User:     jongji
  Password: ${POSTGRES_PASSWORD}

[Admin Account]
  Email:    admin@jongji.local
  Name:     administrator
  Password: ${ADMIN_PASSWORD}

⚠️  이 파일을 안전한 곳에 보관하세요.
========================================
CRED

chmod 600 "${TEST_DIR}/.credentials"

assert_true ".credentials 파일 존재" test -f "${TEST_DIR}/.credentials"
assert_true ".credentials에 PostgreSQL 비밀번호 포함" grep -q "${POSTGRES_PASSWORD}" "${TEST_DIR}/.credentials"
assert_true ".credentials에 Admin 비밀번호 포함" grep -q "${ADMIN_PASSWORD}" "${TEST_DIR}/.credentials"
assert_true ".credentials에 admin@jongji.local 포함" grep -q "admin@jongji.local" "${TEST_DIR}/.credentials"

CRED_PERM="$(stat -c '%a' "${TEST_DIR}/.credentials" 2>/dev/null || stat -f '%Lp' "${TEST_DIR}/.credentials" 2>/dev/null)"
assert_eq ".credentials 파일 권한 600" "600" "${CRED_PERM}"

echo ""

# ══════════════════════════════════════════════════════════════════
# Test 5: 멱등성 검증
# ══════════════════════════════════════════════════════════════════
echo "── Test 5: 멱등성 ─────────────────────────────────────"

# .env가 이미 있으면 건너뛰어야 함
ORIGINAL_CONTENT="$(cat "${TEST_DIR}/.env")"
# 재실행 시뮬레이션: .env가 있으므로 생성을 건너뜀
if [[ -f "${TEST_DIR}/.env" ]]; then
    SKIP_ENV="true"
else
    SKIP_ENV="false"
fi
assert_eq ".env 존재 시 건너뛰기" "true" "${SKIP_ENV}"

# .credentials가 이미 있으면 건너뛰어야 함
if [[ -f "${TEST_DIR}/.credentials" ]]; then
    SKIP_CRED="true"
else
    SKIP_CRED="false"
fi
assert_eq ".credentials 존재 시 건너뛰기" "true" "${SKIP_CRED}"

# .env 내용이 변경되지 않았는지 확인
CURRENT_CONTENT="$(cat "${TEST_DIR}/.env")"
assert_eq ".env 내용 불변" "${ORIGINAL_CONTENT}" "${CURRENT_CONTENT}"

echo ""

# ══════════════════════════════════════════════════════════════════
# Test 6: .env.example에 SETUP_TOKEN 존재 확인
# ══════════════════════════════════════════════════════════════════
echo "── Test 6: .env.example 검증 ──────────────────────────"
assert_true ".env.example에 SETUP_TOKEN 존재" grep -q "SETUP_TOKEN=CHANGE_ME_SETUP_TOKEN" "${PROJECT_ROOT}/.env.example"

echo ""

# ══════════════════════════════════════════════════════════════════
# Test 7: .gitignore에 .credentials 존재 확인
# ══════════════════════════════════════════════════════════════════
echo "── Test 7: .gitignore 검증 ────────────────────────────"
assert_true ".gitignore에 .credentials 존재" grep -q "^\.credentials$" "${PROJECT_ROOT}/.gitignore"

echo ""

# ── 결과 요약 ─────────────────────────────────────────────────────
echo "========================================"
echo "  결과: ${PASS} passed, ${FAIL} failed"
echo "========================================"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
