"""MCP 태스크 관련 도구 모듈.

업무 CRUD, 이력 조회, 라벨 관리, 내보내기 도구를 제공합니다.
"""

from typing import Any

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from jongji.mcp.tools.common import (
    _handle_tool_error,
    _require_user,
    _session_factory,
    mcp,
    validate_uuid,
)
from jongji.models.task import TaskHistory, TaskLabel


@mcp.tool()
async def create_task(
    api_key: str,
    project_id: str,
    title: str,
    description: str = "",
    priority: int = 5,
    assignee_id: str = "",
) -> dict[str, Any]:
    """새 업무를 생성합니다.

    Args:
        api_key: 사용자 API 키.
        project_id: 프로젝트 UUID 문자열.
        title: 업무 제목.
        description: 업무 설명 (선택).
        priority: 우선순위 1-9 (기본값 5).
        assignee_id: 담당자 UUID 문자열 (선택).

    Returns:
        생성된 업무 정보 딕셔너리.
    """
    from jongji.models.enums import TaskStatus
    from jongji.schemas.task import TaskCreate
    from jongji.services import task_service

    async with _session_factory() as db:
        try:
            user = await _require_user(api_key, db)
            proj_uuid = validate_uuid(project_id, "project_id")

            data = TaskCreate(
                title=title,
                description=description or None,
                priority=priority,
                assignee_id=validate_uuid(assignee_id, "assignee_id") if assignee_id else None,
            )
            task = await task_service.create_task(proj_uuid, data, user.id, db)
            await db.commit()
            return {
                "id": str(task.id),
                "number": task.number,
                "title": task.title,
                "status": TaskStatus.BACKLOG.value,
                "priority": task.priority,
            }
        except PermissionError as e:
            logger.warning(f"create_task 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            logger.warning(f"create_task 검증 실패: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            return _handle_tool_error("create_task", e)
        except Exception as e:
            return _handle_tool_error("create_task", e)


@mcp.tool()
async def update_task(
    api_key: str,
    task_id: str,
    title: str = "",
    description: str = "",
    status: str = "",
    priority: int = 0,
    assignee_id: str = "",
) -> dict[str, Any]:
    """업무를 수정합니다 (제목, 설명, 상태, 우선순위, 담당자).

    Args:
        api_key: 사용자 API 키.
        task_id: 업무 UUID 문자열.
        title: 새 제목 (비어 있으면 변경 안 함).
        description: 새 설명 (비어 있으면 변경 안 함).
        status: 새 상태 값 (비어 있으면 변경 안 함).
        priority: 새 우선순위 1-9 (0이면 변경 안 함).
        assignee_id: 새 담당자 UUID (비어 있으면 변경 안 함).

    Returns:
        수정된 업무 정보 딕셔너리.
    """
    from jongji.schemas.task import TaskUpdate
    from jongji.services import task_service

    async with _session_factory() as db:
        try:
            user = await _require_user(api_key, db)
            task_uuid = validate_uuid(task_id, "task_id")

            update_kwargs: dict[str, Any] = {}
            if title:
                update_kwargs["title"] = title
            if description:
                update_kwargs["description"] = description
            if status:
                update_kwargs["status"] = status
            if priority:
                update_kwargs["priority"] = priority
            if assignee_id:
                update_kwargs["assignee_id"] = validate_uuid(assignee_id, "assignee_id")

            data = TaskUpdate(**update_kwargs)
            task = await task_service.update_task(task_uuid, data, user, db)
            await db.commit()
            return {
                "id": str(task.id),
                "title": task.title,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "priority": task.priority,
            }
        except PermissionError as e:
            logger.warning(f"update_task 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            logger.warning(f"update_task 검증 실패: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            return _handle_tool_error("update_task", e)
        except Exception as e:
            return _handle_tool_error("update_task", e)


@mcp.tool()
async def get_task(api_key: str, task_id: str) -> dict[str, Any]:
    """업무 상세 정보를 조회합니다.

    Args:
        api_key: 사용자 API 키.
        task_id: 업무 UUID 문자열.

    Returns:
        업무 상세 딕셔너리.
    """
    from jongji.services import task_service

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            task_uuid = validate_uuid(task_id, "task_id")
            task = await task_service.get_task(task_uuid, db)
            if not task:
                return {"error": "업무를 찾을 수 없습니다."}

            labels = []
            for tl in task.labels:
                label = getattr(tl, "label", None)
                labels.append({
                    "label_id": str(tl.label_id),
                    "name": label.name if label else None,
                    "color": label.color if label else None,
                })

            return {
                "id": str(task.id),
                "project_id": str(task.project_id),
                "number": task.number,
                "title": task.title,
                "description": task.description,
                "status": task.status.value if hasattr(task.status, "value") else task.status,
                "priority": task.priority,
                "creator_id": str(task.creator_id),
                "assignee_id": str(task.assignee_id) if task.assignee_id else None,
                "start_date": task.start_date.isoformat() if task.start_date else None,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "is_archived": task.is_archived,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "labels": labels,
            }
        except PermissionError as e:
            logger.warning(f"get_task 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            logger.warning(f"get_task 입력 검증 실패: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            return _handle_tool_error("get_task", e)
        except Exception as e:
            return _handle_tool_error("get_task", e)


@mcp.tool()
async def list_tasks(
    api_key: str,
    project_id: str,
    status: str = "",
    assignee_id: str = "",
    priority: int = 0,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """프로젝트의 업무 목록을 조회합니다.

    Args:
        api_key: 사용자 API 키.
        project_id: 프로젝트 UUID 문자열.
        status: 상태 필터 (비어 있으면 전체).
        assignee_id: 담당자 UUID 필터 (비어 있으면 전체).
        priority: 우선순위 필터 (0이면 전체).
        limit: 최대 조회 수 (기본값 20).

    Returns:
        업무 정보 딕셔너리 목록.
    """
    from jongji.models.enums import TaskStatus
    from jongji.services import task_service

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            proj_uuid = validate_uuid(project_id, "project_id")

            status_filter = TaskStatus(status) if status else None
            assignee_uuid = validate_uuid(assignee_id, "assignee_id") if assignee_id else None
            priority_filter = priority if priority else None

            tasks, _, _ = await task_service.list_tasks(
                proj_uuid,
                db,
                status=status_filter,
                assignee_id=assignee_uuid,
                priority=priority_filter,
                limit=limit,
            )
            return [
                {
                    "id": str(t.id),
                    "number": t.number,
                    "title": t.title,
                    "status": t.status.value if hasattr(t.status, "value") else t.status,
                    "priority": t.priority,
                    "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                }
                for t in tasks
            ]
        except PermissionError as e:
            logger.warning(f"list_tasks 인증 실패: {e}")
            return [{"error": str(e)}]
        except ValueError as e:
            logger.warning(f"list_tasks 입력 검증 실패: {e}")
            return [{"error": str(e)}]
        except SQLAlchemyError as e:
            return [_handle_tool_error("list_tasks", e)]
        except Exception as e:
            return [_handle_tool_error("list_tasks", e)]


@mcp.tool()
async def get_task_history(api_key: str, task_id: str) -> list[dict[str, Any]]:
    """업무 변경 이력을 조회합니다.

    Args:
        api_key: 사용자 API 키.
        task_id: 업무 UUID 문자열.

    Returns:
        변경 이력 딕셔너리 목록.
    """
    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            task_uuid = validate_uuid(task_id, "task_id")
            result = await db.execute(
                select(TaskHistory)
                .where(TaskHistory.task_id == task_uuid)
                .order_by(TaskHistory.created_at.asc())
            )
            history = result.scalars().all()
            return [
                {
                    "id": str(h.id),
                    "user_id": str(h.user_id),
                    "field": h.field,
                    "old_value": h.old_value,
                    "new_value": h.new_value,
                    "created_at": h.created_at.isoformat(),
                }
                for h in history
            ]
        except PermissionError as e:
            logger.warning(f"get_task_history 인증 실패: {e}")
            return [{"error": str(e)}]
        except ValueError as e:
            logger.warning(f"get_task_history 입력 검증 실패: {e}")
            return [{"error": str(e)}]
        except SQLAlchemyError as e:
            return [_handle_tool_error("get_task_history", e)]
        except Exception as e:
            return [_handle_tool_error("get_task_history", e)]


@mcp.tool()
async def list_labels(api_key: str, project_id: str) -> list[dict[str, Any]]:
    """프로젝트의 라벨 목록을 조회합니다.

    Args:
        api_key: 사용자 API 키.
        project_id: 프로젝트 UUID 문자열.

    Returns:
        라벨 정보 딕셔너리 목록.
    """
    from jongji.services import label_service

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            proj_uuid = validate_uuid(project_id, "project_id")
            labels = await label_service.list_labels(proj_uuid, db)
            return [
                {
                    "id": str(lbl.id),
                    "name": lbl.name,
                    "color": lbl.color,
                    "created_at": lbl.created_at.isoformat(),
                }
                for lbl in labels
            ]
        except PermissionError as e:
            logger.warning(f"list_labels 인증 실패: {e}")
            return [{"error": str(e)}]
        except ValueError as e:
            logger.warning(f"list_labels 입력 검증 실패: {e}")
            return [{"error": str(e)}]
        except SQLAlchemyError as e:
            return [_handle_tool_error("list_labels", e)]
        except Exception as e:
            return [_handle_tool_error("list_labels", e)]


@mcp.tool()
async def add_label(api_key: str, task_id: str, label_id: str) -> dict[str, Any]:
    """업무에 라벨을 추가합니다.

    Args:
        api_key: 사용자 API 키.
        task_id: 업무 UUID 문자열.
        label_id: 라벨 UUID 문자열.

    Returns:
        결과 딕셔너리 (success 또는 error 키).
    """
    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            task_uuid = validate_uuid(task_id, "task_id")
            label_uuid = validate_uuid(label_id, "label_id")

            existing = await db.execute(
                select(TaskLabel).where(
                    TaskLabel.task_id == task_uuid,
                    TaskLabel.label_id == label_uuid,
                )
            )
            if existing.scalar_one_or_none():
                return {"success": True, "message": "이미 추가된 라벨입니다."}

            db.add(TaskLabel(task_id=task_uuid, label_id=label_uuid))
            await db.flush()
            await db.commit()
            return {"success": True, "task_id": task_id, "label_id": label_id}
        except PermissionError as e:
            logger.warning(f"add_label 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            logger.warning(f"add_label 입력 검증 실패: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            return _handle_tool_error("add_label", e)
        except Exception as e:
            return _handle_tool_error("add_label", e)


@mcp.tool()
async def remove_label(api_key: str, task_id: str, label_id: str) -> dict[str, Any]:
    """업무에서 라벨을 제거합니다.

    Args:
        api_key: 사용자 API 키.
        task_id: 업무 UUID 문자열.
        label_id: 라벨 UUID 문자열.

    Returns:
        결과 딕셔너리 (success 또는 error 키).
    """
    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            task_uuid = validate_uuid(task_id, "task_id")
            label_uuid = validate_uuid(label_id, "label_id")

            result = await db.execute(
                select(TaskLabel).where(
                    TaskLabel.task_id == task_uuid,
                    TaskLabel.label_id == label_uuid,
                )
            )
            if not result.scalar_one_or_none():
                return {"error": "해당 라벨이 업무에 없습니다."}

            await db.execute(
                delete(TaskLabel).where(
                    TaskLabel.task_id == task_uuid,
                    TaskLabel.label_id == label_uuid,
                )
            )
            await db.commit()
            return {"success": True, "task_id": task_id, "label_id": label_id}
        except PermissionError as e:
            logger.warning(f"remove_label 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            logger.warning(f"remove_label 입력 검증 실패: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            return _handle_tool_error("remove_label", e)
        except Exception as e:
            return _handle_tool_error("remove_label", e)


@mcp.tool()
async def export_task(
    api_key: str,
    task_id: str,
    output_format: str = "json",
) -> dict[str, Any] | str:
    """업무를 JSON 또는 Markdown 형식으로 내보냅니다.

    Args:
        api_key: 사용자 API 키.
        task_id: 업무 UUID 문자열.
        output_format: 출력 형식 ("json" 또는 "markdown"), 기본값 "json".

    Returns:
        output_format="json"이면 dict, output_format="markdown"이면 str.
    """
    from jongji.services import export_service

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            task_uuid = validate_uuid(task_id, "task_id")
            return await export_service.export_task(task_uuid, output_format, db)
        except PermissionError as e:
            logger.warning(f"export_task 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            logger.warning(f"export_task 입력 검증 실패: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            return _handle_tool_error("export_task", e)
        except Exception as e:
            return _handle_tool_error("export_task", e)
