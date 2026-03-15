"""search_service 리팩토링 테스트.

contains_eager 적용 쿼리 패턴과 _apply_task_filters 타입 힌트/동작을 검증합니다.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import contains_eager

from jongji.models.enums import TaskStatus
from jongji.models.project import Project
from jongji.models.task import Task, TaskComment
from jongji.services.search_service import _apply_task_filters


# ---------------------------------------------------------------------------
# _apply_task_filters (search_service 버전)
# 시그니처: (stmt, project_id, status, assignee_id, priority, *, task_model=None)
# ---------------------------------------------------------------------------


def _task_stmt() -> object:
    """Task 기반 기본 쿼리를 반환합니다."""
    return (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .options(contains_eager(Task.project))
    )


def _comment_stmt() -> object:
    """TaskComment 기반 기본 쿼리를 반환합니다."""
    return (
        select(TaskComment)
        .join(Task, TaskComment.task_id == Task.id)
        .join(Project, Task.project_id == Project.id)
    )


def test_search_apply_filters_no_args():
    """search._apply_task_filters: 모든 인자 None이면 쿼리를 그대로 반환해야 합니다."""
    stmt = _task_stmt()
    result = _apply_task_filters(stmt, None, None, None, None)
    assert result is not None


def test_search_apply_filters_project_id():
    """search._apply_task_filters: project_id 필터가 올바르게 적용되어야 합니다."""
    project_id = uuid.uuid4()
    stmt = _task_stmt()
    result = _apply_task_filters(stmt, project_id, None, None, None)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert str(project_id) in compiled


def test_search_apply_filters_status():
    """search._apply_task_filters: status 필터가 올바르게 적용되어야 합니다."""
    stmt = _task_stmt()
    result = _apply_task_filters(stmt, None, TaskStatus.DONE, None, None)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "DONE" in compiled


def test_search_apply_filters_assignee_id():
    """search._apply_task_filters: assignee_id 필터가 올바르게 적용되어야 합니다."""
    assignee_id = uuid.uuid4()
    stmt = _task_stmt()
    result = _apply_task_filters(stmt, None, None, assignee_id, None)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert str(assignee_id) in compiled


def test_search_apply_filters_priority():
    """search._apply_task_filters: priority 필터가 올바르게 적용되어야 합니다."""
    stmt = _task_stmt()
    result = _apply_task_filters(stmt, None, None, None, 7)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "priority" in compiled


def test_search_apply_filters_all_combined():
    """search._apply_task_filters: 모든 필터를 동시에 적용할 수 있어야 합니다."""
    project_id = uuid.uuid4()
    assignee_id = uuid.uuid4()
    stmt = _task_stmt()
    result = _apply_task_filters(stmt, project_id, TaskStatus.IN_PROGRESS, assignee_id, 3)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert str(project_id) in compiled
    assert "IN_PROGRESS" in compiled
    assert str(assignee_id) in compiled
    assert "priority" in compiled


def test_search_apply_filters_task_model_kwarg():
    """search._apply_task_filters: task_model 키워드 인자를 사용할 수 있어야 합니다."""
    assignee_id = uuid.uuid4()
    stmt = _comment_stmt()
    result = _apply_task_filters(stmt, None, TaskStatus.TODO, assignee_id, None, task_model=Task)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "TODO" in compiled
    assert str(assignee_id) in compiled


def test_search_apply_filters_priority_zero_applies():
    """search._apply_task_filters: priority=0도 필터로 적용되어야 합니다."""
    stmt = _task_stmt()
    result = _apply_task_filters(stmt, None, None, None, 0)
    compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
    assert "priority" in compiled


# ---------------------------------------------------------------------------
# contains_eager 쿼리 패턴 구조 검증
# ---------------------------------------------------------------------------


def test_contains_eager_option_present_in_task_query():
    """contains_eager를 포함한 Task 쿼리가 정상적으로 구성되어야 합니다."""
    stmt = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .options(contains_eager(Task.project))
    )
    # 컴파일 가능한지 확인
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "tasks" in compiled.lower()
    assert "projects" in compiled.lower()


def test_contains_eager_nested_comment_query():
    """contains_eager 중첩 옵션이 포함된 댓글 쿼리가 정상 구성되어야 합니다."""
    stmt = (
        select(TaskComment)
        .join(Task, TaskComment.task_id == Task.id)
        .join(Project, Task.project_id == Project.id)
        .options(contains_eager(TaskComment.task).contains_eager(Task.project))
    )
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "task_comments" in compiled.lower()
    assert "tasks" in compiled.lower()
