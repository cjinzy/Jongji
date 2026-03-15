"""task_service 내부 헬퍼 함수 단위 테스트.

_apply_task_filters, _validate_assignee, _validate_update_fields,
_record_field_changes의 동작을 검증합니다.
"""

import uuid

import pytest
from sqlalchemy import select

from jongji.models.enums import TaskStatus
from jongji.models.project import ProjectMember
from jongji.models.task import Task
from jongji.services.task_service import (
    _apply_task_filters,
    _record_field_changes,
    _validate_assignee,
    _validate_update_fields,
)


# ---------------------------------------------------------------------------
# _apply_task_filters
# ---------------------------------------------------------------------------


def _base_query() -> object:
    """테스트용 기본 SELECT 쿼리를 반환합니다."""
    return select(Task).where(Task.project_id == uuid.uuid4())


def test_apply_task_filters_no_filters():
    """_apply_task_filters: 필터 없으면 쿼리를 그대로 반환해야 합니다."""
    query = _base_query()
    result = _apply_task_filters(query, None, None, None)
    # WHERE 절 개수가 늘지 않아야 함
    assert result is not None


def test_apply_task_filters_status_only():
    """_apply_task_filters: status 필터만 적용할 수 있어야 합니다."""
    query = _base_query()
    result = _apply_task_filters(query, TaskStatus.TODO, None, None)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "TODO" in compiled


def test_apply_task_filters_assignee_only():
    """_apply_task_filters: assignee_id 필터만 적용할 수 있어야 합니다."""
    assignee = uuid.uuid4()
    query = _base_query()
    result = _apply_task_filters(query, None, assignee, None)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert str(assignee) in compiled


def test_apply_task_filters_priority_zero():
    """_apply_task_filters: priority=0도 필터로 적용되어야 합니다."""
    query = _base_query()
    result = _apply_task_filters(query, None, None, 0)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "priority" in compiled


def test_apply_task_filters_all_combined():
    """_apply_task_filters: 모든 필터를 함께 적용할 수 있어야 합니다."""
    assignee = uuid.uuid4()
    query = _base_query()
    result = _apply_task_filters(query, TaskStatus.IN_PROGRESS, assignee, 5)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "IN_PROGRESS" in compiled
    assert str(assignee) in compiled
    assert "priority" in compiled


# ---------------------------------------------------------------------------
# _validate_assignee
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_assignee_none_skips(db_session, project):
    """_validate_assignee: assignee_id=None이면 검증을 건너뛰어야 합니다."""
    # 예외 없이 통과해야 함
    await _validate_assignee(project.id, None, db_session)


@pytest.mark.asyncio
async def test_validate_assignee_valid_member_passes(db_session, project, user_bob):
    """_validate_assignee: 프로젝트 멤버인 사용자는 통과해야 합니다."""
    from jongji.models.enums import ProjectRole

    member = ProjectMember(
        project_id=project.id,
        user_id=user_bob.id,
        role=ProjectRole.MEMBER,
    )
    db_session.add(member)
    await db_session.flush()

    # 예외 없이 통과해야 함
    await _validate_assignee(project.id, user_bob.id, db_session)


@pytest.mark.asyncio
async def test_validate_assignee_non_member_raises(db_session, project):
    """_validate_assignee: 프로젝트 멤버가 아닌 사용자면 ValueError를 발생시켜야 합니다."""
    stranger_id = uuid.uuid4()
    with pytest.raises(ValueError, match="프로젝트 멤버"):
        await _validate_assignee(project.id, stranger_id, db_session)


# ---------------------------------------------------------------------------
# _validate_update_fields
# ---------------------------------------------------------------------------


def test_validate_update_fields_allowed():
    """_validate_update_fields: 허용된 필드만 있으면 예외 없이 통과해야 합니다."""
    _validate_update_fields({"title": "새 제목", "priority": 3})


def test_validate_update_fields_disallowed_raises():
    """_validate_update_fields: 허용되지 않은 필드가 있으면 ValueError를 발생시켜야 합니다."""
    with pytest.raises(ValueError, match="수정할 수 없는 필드"):
        _validate_update_fields({"title": "제목", "status": "DONE"})


def test_validate_update_fields_empty_passes():
    """_validate_update_fields: 빈 딕셔너리는 예외 없이 통과해야 합니다."""
    _validate_update_fields({})


# ---------------------------------------------------------------------------
# _record_field_changes
# ---------------------------------------------------------------------------


def _make_task(**kwargs) -> Task:
    """테스트용 Task 더미 객체를 생성합니다."""
    task = Task.__new__(Task)
    task.id = uuid.uuid4()
    task.title = kwargs.get("title", "원래 제목")
    task.description = kwargs.get("description", "원래 설명")
    task.priority = kwargs.get("priority", 3)
    task.assignee_id = kwargs.get("assignee_id", None)
    task.start_date = kwargs.get("start_date", None)
    task.due_date = kwargs.get("due_date", None)
    return task


def test_record_field_changes_detects_change():
    """_record_field_changes: 변경된 필드에 대한 히스토리 레코드를 생성해야 합니다."""
    task = _make_task(title="기존 제목")
    user_id = uuid.uuid4()

    records = _record_field_changes(task, {"title": "새 제목"}, user_id)

    assert len(records) == 1
    assert records[0].field == "title"
    assert records[0].old_value == "기존 제목"
    assert records[0].new_value == "새 제목"


def test_record_field_changes_no_change_skipped():
    """_record_field_changes: 값이 동일하면 히스토리를 생성하지 않아야 합니다."""
    task = _make_task(title="동일 제목")
    user_id = uuid.uuid4()

    records = _record_field_changes(task, {"title": "동일 제목"}, user_id)

    assert len(records) == 0


def test_record_field_changes_multiple_fields():
    """_record_field_changes: 여러 필드가 변경되면 각각 레코드를 생성해야 합니다."""
    task = _make_task(title="제목", priority=1)
    user_id = uuid.uuid4()

    records = _record_field_changes(task, {"title": "새 제목", "priority": 5}, user_id)

    fields = {r.field for r in records}
    assert "title" in fields
    assert "priority" in fields


def test_record_field_changes_updates_task_attributes():
    """_record_field_changes: 변경 후 task 속성이 새 값으로 갱신되어야 합니다."""
    task = _make_task(title="구 제목")
    user_id = uuid.uuid4()

    _record_field_changes(task, {"title": "신 제목"}, user_id)

    assert task.title == "신 제목"


def test_record_field_changes_none_to_value():
    """_record_field_changes: None에서 값으로 변경 시 히스토리를 생성해야 합니다."""
    task = _make_task(assignee_id=None)
    user_id = uuid.uuid4()
    new_assignee = uuid.uuid4()

    records = _record_field_changes(task, {"assignee_id": new_assignee}, user_id)

    assert len(records) == 1
    assert records[0].old_value is None
    assert records[0].new_value == str(new_assignee)
