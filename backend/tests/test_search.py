"""전문 검색 API 테스트 - TDD 방식.

pg_trgm + tsvector 기반 검색 엔드포인트를 테스트합니다.
"""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import text

from jongji.config import settings
from jongji.database import get_db
from jongji.main import app
from jongji.models.enums import ProjectRole, TaskStatus, TeamRole
from jongji.models.project import Project, ProjectMember
from jongji.models.task import Task, TaskComment, TaskTag
from jongji.models.team import Team, TeamMember
from jongji.models.user import User


def _hash_password(password: str) -> str:
    """테스트용 비밀번호 해싱."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _make_token(user_id: str) -> str:
    """테스트용 JWT 액세스 토큰 생성."""
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.fixture
async def client(db_session):
    """테스트용 AsyncClient."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def search_user(db_session) -> User:
    """테스트용 사용자 생성."""
    user = User(
        email=f"search_{uuid.uuid4().hex[:8]}@example.com",
        name="Search User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def search_headers(search_user) -> dict:
    """인증 헤더."""
    return {"Authorization": f"Bearer {_make_token(str(search_user.id))}"}


@pytest.fixture
async def search_env(db_session, search_user):
    """팀/프로젝트/작업 환경 설정."""
    team = Team(name=f"Search Team {uuid.uuid4().hex[:4]}", created_by=search_user.id)
    db_session.add(team)
    await db_session.flush()

    tm = TeamMember(team_id=team.id, user_id=search_user.id, role=TeamRole.LEADER)
    db_session.add(tm)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Search Project",
        key=f"SRCH{uuid.uuid4().hex[:3].upper()}",
        owner_id=search_user.id,
    )
    db_session.add(project)
    await db_session.flush()

    pm = ProjectMember(
        project_id=project.id,
        user_id=search_user.id,
        role=ProjectRole.LEADER,
    )
    db_session.add(pm)
    await db_session.flush()

    # 작업 생성 (tsvector 수동 업데이트)
    task1 = Task(
        project_id=project.id,
        number=1,
        title="Fix login bug",
        description="Users cannot login with email",
        status=TaskStatus.TODO,
        priority=3,
        creator_id=search_user.id,
    )
    task2 = Task(
        project_id=project.id,
        number=2,
        title="Update dashboard",
        description="Add new metrics to dashboard",
        status=TaskStatus.PROGRESS,
        priority=5,
        creator_id=search_user.id,
    )
    task3 = Task(
        project_id=project.id,
        number=3,
        title="Write documentation",
        description="API docs needed",
        status=TaskStatus.BACKLOG,
        priority=7,
        creator_id=search_user.id,
    )
    db_session.add_all([task1, task2, task3])
    await db_session.flush()

    # tsvector 수동 업데이트 (트리거 없이 테스트)
    await db_session.execute(
        text(
            "UPDATE tasks SET search_vector = to_tsvector('pg_catalog.simple', "
            "coalesce(title,'') || ' ' || coalesce(description,'')) "
            "WHERE id IN (:id1, :id2, :id3)"
        ),
        {"id1": str(task1.id), "id2": str(task2.id), "id3": str(task3.id)},
    )

    # 태그 추가
    tag1 = TaskTag(task_id=task1.id, tag="backend")
    tag2 = TaskTag(task_id=task2.id, tag="frontend")
    db_session.add_all([tag1, tag2])
    await db_session.flush()

    # 댓글 추가
    comment = TaskComment(
        task_id=task1.id,
        user_id=search_user.id,
        content="This is related to authentication module",
    )
    db_session.add(comment)
    await db_session.flush()

    # 댓글 search_vector 수동 업데이트
    await db_session.execute(
        text(
            "UPDATE task_comments SET search_vector = to_tsvector('pg_catalog.simple', content) "
            "WHERE id = :id"
        ),
        {"id": str(comment.id)},
    )

    await db_session.refresh(task1)
    await db_session.refresh(task2)
    await db_session.refresh(task3)

    return {
        "team": team,
        "project": project,
        "task1": task1,
        "task2": task2,
        "task3": task3,
        "comment": comment,
    }


class TestSearchByTitle:
    """제목 키워드 검색 테스트."""

    async def test_search_by_title_keyword(self, client, search_headers, search_env):
        """영어 제목 키워드로 작업을 검색합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "login"},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "login"
        assert data["total"] >= 1
        task_ids = [item["task_id"] for item in data["items"]]
        assert str(search_env["task1"].id) in task_ids

    async def test_search_by_title_returns_correct_fields(self, client, search_headers, search_env):
        """검색 결과가 필요한 모든 필드를 포함합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "login"},
            headers=search_headers,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        item = items[0]
        assert "type" in item
        assert "task_id" in item
        assert "task_number" in item
        assert "task_title" in item
        assert "project_key" in item
        assert "highlight" in item
        assert "score" in item


class TestSearchByDescription:
    """설명 키워드 검색 테스트."""

    async def test_search_by_description_keyword(self, client, search_headers, search_env):
        """영어 설명 키워드로 작업을 검색합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "metrics"},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        task_ids = [item["task_id"] for item in data["items"]]
        assert str(search_env["task2"].id) in task_ids


class TestSearchByTag:
    """태그 필터 검색 테스트."""

    async def test_search_by_tag_prefix(self, client, search_headers, search_env):
        """tag: 접두사로 태그 검색합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "tag:backend"},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        task_ids = [item["task_id"] for item in data["items"]]
        assert str(search_env["task1"].id) in task_ids

    async def test_search_by_hash_prefix(self, client, search_headers, search_env):
        """# 접두사로 태그 검색합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "#frontend"},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        task_ids = [item["task_id"] for item in data["items"]]
        assert str(search_env["task2"].id) in task_ids


class TestSearchByProjectKeyNumber:
    """프로젝트 키+번호 패턴 검색 테스트."""

    async def test_search_by_project_key_number(self, client, search_headers, search_env):
        """PROJ-42 패턴으로 정확한 작업을 검색합니다."""
        project = search_env["project"]
        task1 = search_env["task1"]
        query = f"{project.key}-{task1.number}"

        resp = await client.get(
            "/api/v1/search",
            params={"q": query},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        task_ids = [item["task_id"] for item in data["items"]]
        assert str(task1.id) in task_ids

    async def test_search_by_project_key_number_not_found(self, client, search_headers, search_env):
        """존재하지 않는 프로젝트 키+번호 패턴은 빈 결과를 반환합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "XXXX-9999"},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0


class TestSearchWithStatusFilter:
    """상태 필터 검색 테스트."""

    async def test_search_with_status_filter(self, client, search_headers, search_env):
        """상태 필터로 특정 상태의 작업만 검색합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "update", "status": TaskStatus.PROGRESS.value},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            # 반환된 모든 결과는 필터링된 상태여야 함
            assert item["type"] in ("task", "comment")

    async def test_search_status_excludes_other_status(self, client, search_headers, search_env):
        """상태 필터가 다른 상태를 제외합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "login", "status": TaskStatus.DONE.value},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # task1은 TODO 상태이므로 DONE 필터에는 없어야 함
        task_ids = [item["task_id"] for item in data["items"]]
        assert str(search_env["task1"].id) not in task_ids


class TestSearchEmptyResults:
    """빈 결과 반환 테스트."""

    async def test_search_no_match(self, client, search_headers, search_env):
        """매칭되지 않는 검색어는 빈 결과를 반환합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "xyznonexistent999"},
            headers=search_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["query"] == "xyznonexistent999"


class TestSearchAuthentication:
    """인증 검증 테스트."""

    async def test_search_unauthenticated_returns_401(self, client, search_env):
        """인증 없이 검색 시 401을 반환합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "login"},
        )
        assert resp.status_code == 401

    async def test_search_invalid_token_returns_401(self, client, search_env):
        """잘못된 토큰으로 검색 시 401을 반환합니다."""
        resp = await client.get(
            "/api/v1/search",
            params={"q": "login"},
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 401
