"""member_mixin 헬퍼 함수 단위 테스트.

fetch_member_or_none, assert_not_duplicate, delete_member_or_raise,
fetch_user_or_raise, build_member_dict의 동작을 검증합니다.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from jongji.models.project import ProjectMember
from jongji.models.user import User
from jongji.services.member_mixin import (
    assert_not_duplicate,
    build_member_dict,
    delete_member_or_raise,
    fetch_member_or_none,
    fetch_user_or_raise,
)


# ---------------------------------------------------------------------------
# fetch_user_or_raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_user_or_raise_returns_user(db_session, user_alice):
    """fetch_user_or_raise: 존재하는 사용자를 반환해야 합니다."""
    user = await fetch_user_or_raise(user_alice.id, db_session)
    assert user.id == user_alice.id
    assert user.email == user_alice.email


@pytest.mark.asyncio
async def test_fetch_user_or_raise_missing_raises(db_session):
    """fetch_user_or_raise: 존재하지 않는 사용자면 ValueError를 발생시켜야 합니다."""
    nonexistent_id = uuid.uuid4()
    with pytest.raises(ValueError, match="사용자를 찾을 수 없습니다"):
        await fetch_user_or_raise(nonexistent_id, db_session)


# ---------------------------------------------------------------------------
# fetch_member_or_none
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_member_or_none_found(db_session, project, user_alice):
    """fetch_member_or_none: 존재하는 멤버를 반환해야 합니다."""
    from jongji.models.enums import ProjectRole

    member = ProjectMember(
        project_id=project.id,
        user_id=user_alice.id,
        role=ProjectRole.MEMBER,
    )
    db_session.add(member)
    await db_session.flush()

    result = await fetch_member_or_none(
        ProjectMember,
        (ProjectMember.project_id == project.id)
        & (ProjectMember.user_id == user_alice.id),
        db_session,
    )
    assert result is not None
    assert result.user_id == user_alice.id


@pytest.mark.asyncio
async def test_fetch_member_or_none_not_found(db_session, project):
    """fetch_member_or_none: 존재하지 않으면 None을 반환해야 합니다."""
    result = await fetch_member_or_none(
        ProjectMember,
        ProjectMember.project_id == uuid.uuid4(),
        db_session,
    )
    assert result is None


# ---------------------------------------------------------------------------
# assert_not_duplicate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assert_not_duplicate_no_duplicate_passes(db_session, project):
    """assert_not_duplicate: 중복 없으면 예외 없이 통과해야 합니다."""
    await assert_not_duplicate(
        ProjectMember,
        ProjectMember.project_id == uuid.uuid4(),
        "이미 멤버입니다.",
        db_session,
    )


@pytest.mark.asyncio
async def test_assert_not_duplicate_raises_on_duplicate(db_session, project, user_alice):
    """assert_not_duplicate: 중복 멤버가 있으면 ValueError를 발생시켜야 합니다."""
    from jongji.models.enums import ProjectRole

    member = ProjectMember(
        project_id=project.id,
        user_id=user_alice.id,
        role=ProjectRole.MEMBER,
    )
    db_session.add(member)
    await db_session.flush()

    with pytest.raises(ValueError, match="이미 멤버입니다"):
        await assert_not_duplicate(
            ProjectMember,
            (ProjectMember.project_id == project.id)
            & (ProjectMember.user_id == user_alice.id),
            "이미 멤버입니다.",
            db_session,
        )


# ---------------------------------------------------------------------------
# delete_member_or_raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_member_or_raise_deletes_existing(db_session, project, user_alice):
    """delete_member_or_raise: 존재하는 멤버를 삭제해야 합니다."""
    from jongji.models.enums import ProjectRole

    member = ProjectMember(
        project_id=project.id,
        user_id=user_alice.id,
        role=ProjectRole.MEMBER,
    )
    db_session.add(member)
    await db_session.flush()

    await delete_member_or_raise(
        ProjectMember,
        (ProjectMember.project_id == project.id)
        & (ProjectMember.user_id == user_alice.id),
        "멤버를 찾을 수 없습니다.",
        db_session,
    )

    # 삭제 후 조회 시 None이어야 함
    result = await fetch_member_or_none(
        ProjectMember,
        (ProjectMember.project_id == project.id)
        & (ProjectMember.user_id == user_alice.id),
        db_session,
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete_member_or_raise_missing_raises(db_session):
    """delete_member_or_raise: 존재하지 않는 멤버면 ValueError를 발생시켜야 합니다."""
    with pytest.raises(ValueError, match="멤버를 찾을 수 없습니다"):
        await delete_member_or_raise(
            ProjectMember,
            ProjectMember.project_id == uuid.uuid4(),
            "멤버를 찾을 수 없습니다.",
            db_session,
        )


# ---------------------------------------------------------------------------
# build_member_dict
# ---------------------------------------------------------------------------


def test_build_member_dict_with_min_alert_priority():
    """build_member_dict: min_alert_priority 속성이 있는 모델을 올바르게 변환해야 합니다."""
    pm = MagicMock()
    pm.id = uuid.uuid4()
    pm.user_id = uuid.uuid4()
    pm.role = "member"
    pm.min_alert_priority = 3
    pm.created_at = None

    user = MagicMock(spec=User)
    user.name = "Alice"
    user.email = "alice@example.com"

    result = build_member_dict(pm, user)

    assert result["id"] == pm.id
    assert result["user_id"] == pm.user_id
    assert result["user_name"] == "Alice"
    assert result["user_email"] == "alice@example.com"
    assert result["role"] == "member"
    assert result["min_alert_priority"] == 3
    assert result["created_at"] is None


def test_build_member_dict_without_min_alert_priority():
    """build_member_dict: min_alert_priority 없는 모델(TeamMember 등)은 None으로 처리해야 합니다."""
    pm = MagicMock(spec=["id", "user_id", "role", "created_at"])
    pm.id = uuid.uuid4()
    pm.user_id = uuid.uuid4()
    pm.role = "leader"
    pm.created_at = None

    user = MagicMock(spec=User)
    user.name = "Bob"
    user.email = "bob@example.com"

    result = build_member_dict(pm, user)

    assert result["min_alert_priority"] is None
    assert result["user_name"] == "Bob"
    assert result["role"] == "leader"
