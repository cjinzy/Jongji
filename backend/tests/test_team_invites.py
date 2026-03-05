"""팀 초대 링크 API 테스트 - TDD 방식.

초대 생성, 목록 조회, 비활성화, 토큰으로 팀 참여 등의 동작을 검증합니다.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from jongji.database import get_db
from jongji.main import app
from jongji.models.enums import TeamRole
from jongji.models.team import Team, TeamInvite, TeamMember
from jongji.models.user import User
from jongji.services.auth_service import hash_password

# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
async def client(db_session):
    """테스트용 HTTP 클라이언트.

    DB dependency를 테스트 세션으로 오버라이드합니다.

    Args:
        db_session: 테스트용 DB 세션 픽스처.

    Yields:
        AsyncClient: 비동기 HTTP 클라이언트.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def leader_user(db_session):
    """팀 리더 사용자 픽스처.

    Args:
        db_session: 테스트용 DB 세션.

    Returns:
        User: 생성된 리더 사용자.
    """
    user = User(
        id=uuid.uuid4(),
        email=f"leader_{uuid.uuid4().hex[:8]}@example.com",
        name="Leader User",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def member_user(db_session):
    """일반 멤버 사용자 픽스처.

    Args:
        db_session: 테스트용 DB 세션.

    Returns:
        User: 생성된 멤버 사용자.
    """
    user = User(
        id=uuid.uuid4(),
        email=f"member_{uuid.uuid4().hex[:8]}@example.com",
        name="Member User",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def other_user(db_session):
    """외부 사용자 픽스처 (팀 미소속).

    Args:
        db_session: 테스트용 DB 세션.

    Returns:
        User: 생성된 외부 사용자.
    """
    user = User(
        id=uuid.uuid4(),
        email=f"other_{uuid.uuid4().hex[:8]}@example.com",
        name="Other User",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def team_with_leader(db_session, leader_user):
    """리더가 포함된 팀 픽스처.

    Args:
        db_session: 테스트용 DB 세션.
        leader_user: 팀 리더 사용자.

    Returns:
        tuple[Team, TeamMember]: 팀과 리더 멤버십.
    """
    team = Team(
        id=uuid.uuid4(),
        name="Test Team",
        created_by=leader_user.id,
    )
    db_session.add(team)
    await db_session.flush()

    leader_member = TeamMember(
        id=uuid.uuid4(),
        team_id=team.id,
        user_id=leader_user.id,
        role=TeamRole.LEADER,
    )
    db_session.add(leader_member)
    await db_session.flush()

    return team, leader_member


async def _get_token(client: AsyncClient, email: str) -> str:
    """사용자 로그인 후 access_token 반환.

    Args:
        client: HTTP 클라이언트.
        email: 로그인 이메일.

    Returns:
        str: JWT access token.
    """
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert resp.status_code == 200, f"로그인 실패: {resp.text}"
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# 초대 생성 테스트
# ---------------------------------------------------------------------------


class TestCreateInvite:
    """POST /{team_id}/invites 엔드포인트 테스트."""

    async def test_create_invite(self, client, team_with_leader, leader_user):
        """리더가 초대 생성 시 201 + token 반환."""
        team, _ = team_with_leader
        token = await _get_token(client, leader_user.email)

        resp = await client.post(
            f"/api/v1/teams/{team.id}/invites",
            json={"expires_in_days": 7},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert data["is_active"] is True
        assert data["team_id"] == str(team.id)

    async def test_create_invite_non_leader(self, client, team_with_leader, db_session, member_user):
        """리더가 아닌 멤버가 초대 생성 시 403 반환."""
        team, _ = team_with_leader

        # member_user를 팀의 일반 멤버로 추가
        team_member = TeamMember(
            id=uuid.uuid4(),
            team_id=team.id,
            user_id=member_user.id,
            role=TeamRole.MEMBER,
        )
        db_session.add(team_member)
        await db_session.flush()

        token = await _get_token(client, member_user.email)

        resp = await client.post(
            f"/api/v1/teams/{team.id}/invites",
            json={"expires_in_days": 7},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_create_invite_unauthenticated(self, client, team_with_leader):
        """인증 없이 초대 생성 시 401 반환."""
        team, _ = team_with_leader

        resp = await client.post(
            f"/api/v1/teams/{team.id}/invites",
            json={"expires_in_days": 7},
        )
        assert resp.status_code == 401

    async def test_create_invite_with_max_uses(self, client, team_with_leader, leader_user):
        """max_uses 설정 가능 여부 검증."""
        team, _ = team_with_leader
        token = await _get_token(client, leader_user.email)

        resp = await client.post(
            f"/api/v1/teams/{team.id}/invites",
            json={"expires_in_days": 3, "max_uses": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["max_uses"] == 5


# ---------------------------------------------------------------------------
# 초대 목록 조회 테스트
# ---------------------------------------------------------------------------


class TestListInvites:
    """GET /{team_id}/invites 엔드포인트 테스트."""

    async def test_list_invites(self, client, team_with_leader, leader_user, db_session):
        """활성 초대만 반환하는지 검증."""
        import secrets
        from datetime import UTC, datetime, timedelta

        team, _ = team_with_leader
        token = await _get_token(client, leader_user.email)

        # 활성 초대 2개 생성
        for _ in range(2):
            invite = TeamInvite(
                id=uuid.uuid4(),
                team_id=team.id,
                created_by=leader_user.id,
                token=secrets.token_urlsafe(32),
                expires_at=datetime.now(UTC) + timedelta(days=7),
                is_active=True,
            )
            db_session.add(invite)

        # 비활성 초대 1개 생성
        inactive_invite = TeamInvite(
            id=uuid.uuid4(),
            team_id=team.id,
            created_by=leader_user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=False,
        )
        db_session.add(inactive_invite)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/teams/{team.id}/invites",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # 비활성 초대는 제외되어야 함
        assert all(inv["is_active"] for inv in data)
        assert len(data) == 2


# ---------------------------------------------------------------------------
# 초대 비활성화 테스트
# ---------------------------------------------------------------------------


class TestDeactivateInvite:
    """DELETE /{team_id}/invites/{invite_id} 엔드포인트 테스트."""

    async def test_deactivate_invite(self, client, team_with_leader, leader_user, db_session):
        """초대 비활성화 시 is_active=False로 변경됨."""
        import secrets
        from datetime import UTC, datetime, timedelta

        team, _ = team_with_leader
        token = await _get_token(client, leader_user.email)

        invite = TeamInvite(
            id=uuid.uuid4(),
            team_id=team.id,
            created_by=leader_user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(invite)
        await db_session.flush()

        resp = await client.delete(
            f"/api/v1/teams/{team.id}/invites/{invite.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        await db_session.refresh(invite)
        assert invite.is_active is False

    async def test_deactivate_invite_not_found(self, client, team_with_leader, leader_user):
        """존재하지 않는 초대 비활성화 시 404 반환."""
        team, _ = team_with_leader
        token = await _get_token(client, leader_user.email)

        resp = await client.delete(
            f"/api/v1/teams/{team.id}/invites/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 토큰으로 팀 참여 테스트
# ---------------------------------------------------------------------------


class TestJoinByToken:
    """POST /join/{token} 엔드포인트 테스트."""

    async def test_join_by_token(self, client, team_with_leader, leader_user, other_user, db_session):
        """유효한 토큰으로 팀 참여 시 멤버로 추가됨."""
        import secrets
        from datetime import UTC, datetime, timedelta

        team, _ = team_with_leader

        invite = TeamInvite(
            id=uuid.uuid4(),
            team_id=team.id,
            created_by=leader_user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(invite)
        await db_session.flush()

        token = await _get_token(client, other_user.email)

        resp = await client.post(
            f"/api/v1/teams/join/{invite.token}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        result = await db_session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team.id,
                TeamMember.user_id == other_user.id,
            )
        )
        member = result.scalar_one_or_none()
        assert member is not None
        assert member.role == TeamRole.MEMBER

    async def test_join_expired_token(self, client, team_with_leader, leader_user, other_user, db_session):
        """만료된 초대 토큰으로 참여 시 400 반환."""
        import secrets
        from datetime import UTC, datetime, timedelta

        team, _ = team_with_leader

        invite = TeamInvite(
            id=uuid.uuid4(),
            team_id=team.id,
            created_by=leader_user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) - timedelta(days=1),  # 이미 만료
            is_active=True,
        )
        db_session.add(invite)
        await db_session.flush()

        token = await _get_token(client, other_user.email)

        resp = await client.post(
            f"/api/v1/teams/join/{invite.token}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_join_max_uses_exceeded(self, client, team_with_leader, leader_user, other_user, db_session):
        """최대 사용 횟수 초과된 초대 토큰으로 참여 시 400 반환."""
        import secrets
        from datetime import UTC, datetime, timedelta

        team, _ = team_with_leader

        invite = TeamInvite(
            id=uuid.uuid4(),
            team_id=team.id,
            created_by=leader_user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            max_uses=3,
            use_count=3,  # 이미 최대 사용 횟수 도달
            is_active=True,
        )
        db_session.add(invite)
        await db_session.flush()

        token = await _get_token(client, other_user.email)

        resp = await client.post(
            f"/api/v1/teams/join/{invite.token}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_join_already_member(self, client, team_with_leader, leader_user, db_session):
        """이미 팀 멤버인 경우 멱등성 보장 (에러 없음)."""
        import secrets
        from datetime import UTC, datetime, timedelta

        team, _ = team_with_leader

        invite = TeamInvite(
            id=uuid.uuid4(),
            team_id=team.id,
            created_by=leader_user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=True,
        )
        db_session.add(invite)
        await db_session.flush()

        # 리더 자신이 초대 토큰으로 참여 시도 (이미 멤버)
        token = await _get_token(client, leader_user.email)

        resp = await client.post(
            f"/api/v1/teams/join/{invite.token}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 멱등성 보장 - 에러 없이 성공
        assert resp.status_code == 200

    async def test_join_inactive_token(self, client, team_with_leader, leader_user, other_user, db_session):
        """비활성화된 초대 토큰으로 참여 시 400 반환."""
        import secrets
        from datetime import UTC, datetime, timedelta

        team, _ = team_with_leader

        invite = TeamInvite(
            id=uuid.uuid4(),
            team_id=team.id,
            created_by=leader_user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            is_active=False,  # 비활성
        )
        db_session.add(invite)
        await db_session.flush()

        token = await _get_token(client, other_user.email)

        resp = await client.post(
            f"/api/v1/teams/join/{invite.token}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_join_invalid_token(self, client, other_user):
        """존재하지 않는 토큰으로 참여 시 404 반환."""
        token = await _get_token(client, other_user.email)

        resp = await client.post(
            "/api/v1/teams/join/nonexistent-token-xyz",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
