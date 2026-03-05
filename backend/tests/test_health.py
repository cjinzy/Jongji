"""헬스체크 API 엔드포인트 테스트.

/health 및 /ready 엔드포인트의 응답을 검증합니다.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from jongji.main import app


@pytest.fixture
async def client(db_session):
    """테스트용 HTTP 클라이언트.

    DB dependency를 테스트 세션으로 오버라이드합니다.

    Args:
        db_session: 테스트용 DB 세션 픽스처.

    Yields:
        AsyncClient: 비동기 HTTP 클라이언트.
    """
    from jongji.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestHealthCheck:
    """GET /api/v1/health 엔드포인트 테스트."""

    async def test_health_returns_200(self, client):
        """항상 200과 {"status": "ok"}를 반환해야 한다."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_health_no_auth_required(self, client):
        """인증 없이도 접근 가능해야 한다."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200


class TestReadinessCheck:
    """GET /api/v1/ready 엔드포인트 테스트."""

    async def test_ready_returns_200_when_db_ok(self, client):
        """DB 연결이 정상이면 200과 {"status": "ok"}를 반환해야 한다."""
        resp = await client.get("/api/v1/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_ready_no_auth_required(self, client):
        """인증 없이도 접근 가능해야 한다."""
        resp = await client.get("/api/v1/ready")
        assert resp.status_code == 200
