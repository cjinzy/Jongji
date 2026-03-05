"""첨부파일 API 테스트.

업로드, 다운로드, 삭제 및 권한/크기/MIME 타입 검증을 테스트합니다.
ORM으로 직접 사용자를 생성하고 JWT를 발급하여 auth 의존성을 우회합니다.
"""

import io
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from jongji.config import settings
from jongji.database import get_db
from jongji.main import app
from jongji.models.enums import ProjectRole, TaskStatus, TeamRole
from jongji.models.project import Project, ProjectMember
from jongji.models.task import Task
from jongji.models.team import Team, TeamMember
from jongji.models.user import User


def _hash_password(password: str) -> str:
    """테스트용 비밀번호 해싱."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _make_token(user_id: str) -> str:
    """테스트용 JWT 액세스 토큰을 생성합니다."""
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _make_file(
    content: bytes = b"hello world",
    filename: str = "test.txt",
    content_type: str = "text/plain",
) -> dict:
    """테스트용 multipart 파일 튜플을 반환합니다."""
    return {"file": (filename, io.BytesIO(content), content_type)}


@pytest.fixture
async def client(db_session):
    """테스트용 AsyncClient 픽스처."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def uploader(db_session) -> User:
    """파일 업로더 사용자."""
    user = User(
        email=f"uploader_{uuid.uuid4().hex[:8]}@example.com",
        name="Uploader",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session) -> User:
    """다른 사용자 (업로더가 아님)."""
    user = User(
        email=f"other_{uuid.uuid4().hex[:8]}@example.com",
        name="OtherUser",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def task_env(db_session, uploader) -> dict:
    """테스트용 팀/프로젝트/작업 환경을 생성합니다."""
    team = Team(name=f"Attach Team {uuid.uuid4().hex[:6]}", created_by=uploader.id)
    db_session.add(team)
    await db_session.flush()

    tm = TeamMember(team_id=team.id, user_id=uploader.id, role=TeamRole.LEADER)
    db_session.add(tm)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Attach Project",
        key=f"ATT{uuid.uuid4().hex[:4].upper()}",
        owner_id=uploader.id,
    )
    db_session.add(project)
    await db_session.flush()

    pm = ProjectMember(
        project_id=project.id,
        user_id=uploader.id,
        role=ProjectRole.LEADER,
    )
    db_session.add(pm)
    await db_session.flush()

    task = Task(
        project_id=project.id,
        number=1,
        title="Attach Task",
        creator_id=uploader.id,
        status=TaskStatus.BACKLOG,
        priority=5,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)

    return {"team": team, "project": project, "task": task}


class TestTaskAttachmentUpload:
    """POST /api/v1/tasks/{task_id}/attachments 테스트."""

    async def test_upload_task_attachment_success(self, client, uploader, task_env, tmp_path, monkeypatch):
        """업무 첨부파일 업로드 성공."""
        monkeypatch.setattr("jongji.api.attachments.get_storage", lambda: _make_local_storage(tmp_path))

        token = _make_token(str(uploader.id))
        task_id = task_env["task"].id
        files = _make_file(b"file content", "hello.txt", "text/plain")

        resp = await client.post(
            f"/api/v1/tasks/{task_id}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "hello.txt"
        assert data["content_type"] == "text/plain"
        assert data["is_temp"] is False
        assert data["task_id"] == str(task_id)

    async def test_upload_task_attachment_task_not_found(self, client, uploader, tmp_path, monkeypatch):
        """존재하지 않는 작업에 첨부 시 404."""
        monkeypatch.setattr("jongji.api.attachments.get_storage", lambda: _make_local_storage(tmp_path))

        token = _make_token(str(uploader.id))
        files = _make_file()
        resp = await client.post(
            f"/api/v1/tasks/{uuid.uuid4()}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestTempUpload:
    """POST /api/v1/attachments/upload 테스트."""

    async def test_temp_upload_success(self, client, uploader, tmp_path, monkeypatch):
        """임시 업로드 성공 (is_temp=True)."""
        monkeypatch.setattr("jongji.api.attachments.get_storage", lambda: _make_local_storage(tmp_path))

        token = _make_token(str(uploader.id))
        files = _make_file(b"image data", "photo.png", "image/png")

        resp = await client.post(
            "/api/v1/attachments/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_temp"] is True
        assert data["task_id"] is None
        assert data["filename"] == "photo.png"

    async def test_temp_upload_size_exceeded(self, client, uploader, tmp_path, monkeypatch):
        """10MB 초과 파일 업로드 시 413."""
        monkeypatch.setattr("jongji.api.attachments.get_storage", lambda: _make_local_storage(tmp_path))

        token = _make_token(str(uploader.id))
        big_content = b"x" * (10 * 1024 * 1024 + 1)
        files = _make_file(big_content, "big.txt", "text/plain")

        resp = await client.post(
            "/api/v1/attachments/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 413

    async def test_temp_upload_disallowed_mime(self, client, uploader, tmp_path, monkeypatch):
        """허용되지 않는 MIME 타입 시 415."""
        monkeypatch.setattr("jongji.api.attachments.get_storage", lambda: _make_local_storage(tmp_path))

        token = _make_token(str(uploader.id))
        files = _make_file(b"binary", "malware.exe", "application/x-msdownload")

        resp = await client.post(
            "/api/v1/attachments/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 415


class TestDownloadAttachment:
    """GET /api/v1/attachments/{id} 테스트."""

    async def test_download_attachment_success(self, client, uploader, task_env, tmp_path, monkeypatch):
        """파일 다운로드 성공."""
        storage = _make_local_storage(tmp_path)
        monkeypatch.setattr("jongji.api.attachments.get_storage", lambda: storage)

        token = _make_token(str(uploader.id))
        task_id = task_env["task"].id
        content = b"download me"
        files = _make_file(content, "download.txt", "text/plain")

        upload_resp = await client.post(
            f"/api/v1/tasks/{task_id}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upload_resp.status_code == 201
        attachment_id = upload_resp.json()["id"]

        # storage_path는 절대 경로(tmp_path 하위)로 저장되므로 파일이 존재함
        dl_resp = await client.get(
            f"/api/v1/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dl_resp.status_code == 200

    async def test_download_attachment_not_found(self, client, uploader):
        """존재하지 않는 첨부파일 다운로드 시 404."""
        token = _make_token(str(uploader.id))
        resp = await client.get(
            f"/api/v1/attachments/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestDeleteAttachment:
    """DELETE /api/v1/attachments/{id} 테스트."""

    async def test_delete_by_uploader_success(self, client, uploader, task_env, tmp_path, monkeypatch):
        """업로더가 파일 삭제 성공."""
        monkeypatch.setattr("jongji.api.attachments.get_storage", lambda: _make_local_storage(tmp_path))

        token = _make_token(str(uploader.id))
        task_id = task_env["task"].id
        files = _make_file(b"delete me", "del.txt", "text/plain")

        upload_resp = await client.post(
            f"/api/v1/tasks/{task_id}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upload_resp.status_code == 201
        attachment_id = upload_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_resp.status_code == 204

    async def test_delete_by_other_user_forbidden(
        self, client, uploader, other_user, task_env, tmp_path, monkeypatch
    ):
        """다른 사용자가 삭제 시 403."""
        monkeypatch.setattr("jongji.api.attachments.get_storage", lambda: _make_local_storage(tmp_path))

        uploader_token = _make_token(str(uploader.id))
        other_token = _make_token(str(other_user.id))
        task_id = task_env["task"].id
        files = _make_file(b"protected", "protected.txt", "text/plain")

        upload_resp = await client.post(
            f"/api/v1/tasks/{task_id}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {uploader_token}"},
        )
        assert upload_resp.status_code == 201
        attachment_id = upload_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert del_resp.status_code == 403


# --- 헬퍼 ---

def _make_local_storage(tmp_path):
    """테스트용 LocalStorage 인스턴스를 반환합니다."""
    from jongji.services.storage import LocalStorage

    return LocalStorage(upload_dir=str(tmp_path))


