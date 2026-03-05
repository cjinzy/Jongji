"""FastMCP 서버 및 MCP Tool 정의.

사용자별 API Key 인증을 통해 14개의 MCP Tool을 제공합니다.
"""

import hashlib
import traceback
import uuid
from typing import Any

from fastmcp import FastMCP
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from jongji.config import settings
from jongji.models.task import TaskHistory, TaskLabel
from jongji.models.user import User, UserApiKey

mcp = FastMCP("Jongji MCP")

# DB 엔진 (MCP 전용)
_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def _get_user_by_api_key(api_key: str, db: AsyncSession) -> User | None:
    """API Key로 사용자를 조회합니다.

    SHA-256 해시로 key_hash와 비교하여 사용자를 반환합니다.

    Args:
        api_key: 평문 API 키.
        db: 비동기 DB 세션.

    Returns:
        User 객체 또는 None.
    """
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(
        select(UserApiKey)
        .where(UserApiKey.key_hash == key_hash, UserApiKey.is_active.is_(True))
    )
    api_key_obj = result.scalar_one_or_none()
    if not api_key_obj:
        return None

    user_result = await db.execute(
        select(User).where(User.id == api_key_obj.user_id, User.is_active.is_(True))
    )
    return user_result.scalar_one_or_none()


async def _require_user(api_key: str, db: AsyncSession) -> User:
    """API Key 인증 후 사용자를 반환합니다. 인증 실패 시 예외를 발생시킵니다.

    Args:
        api_key: 평문 API 키.
        db: 비동기 DB 세션.

    Returns:
        인증된 User 객체.

    Raises:
        PermissionError: API 키가 유효하지 않은 경우.
    """
    user = await _get_user_by_api_key(api_key, db)
    if not user:
        raise PermissionError("유효하지 않은 API 키입니다.")
    return user


@mcp.tool()
async def list_projects(api_key: str, team_id: str) -> list[dict[str, Any]]:
    """프로젝트 목록을 조회합니다.

    Args:
        api_key: 사용자 API 키.
        team_id: 팀 UUID 문자열.

    Returns:
        프로젝트 정보 딕셔너리 목록.
    """
    from jongji.models.project import Project

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            team_uuid = uuid.UUID(team_id)
            result = await db.execute(
                select(Project).where(
                    Project.team_id == team_uuid,
                    Project.is_archived.is_(False),
                )
            )
            projects = result.scalars().all()
            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "key": p.key,
                    "description": p.description,
                    "is_private": p.is_private,
                    "created_at": p.created_at.isoformat(),
                }
                for p in projects
            ]
        except PermissionError as e:
            logger.warning(f"list_projects 인증 실패: {e}")
            return [{"error": str(e)}]
        except Exception:
            logger.error(f"list_projects 실패: {traceback.format_exc()}")
            return [{"error": "내부 오류가 발생했습니다."}]


@mcp.tool()
async def get_project(api_key: str, project_id: str) -> dict[str, Any]:
    """프로젝트 상세 정보를 조회합니다.

    Args:
        api_key: 사용자 API 키.
        project_id: 프로젝트 UUID 문자열.

    Returns:
        프로젝트 상세 딕셔너리.
    """
    from jongji.models.project import Project

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            proj_uuid = uuid.UUID(project_id)
            result = await db.execute(select(Project).where(Project.id == proj_uuid))
            project = result.scalar_one_or_none()
            if not project:
                return {"error": "프로젝트를 찾을 수 없습니다."}
            return {
                "id": str(project.id),
                "name": project.name,
                "key": project.key,
                "description": project.description,
                "is_private": project.is_private,
                "is_archived": project.is_archived,
                "owner_id": str(project.owner_id),
                "task_counter": project.task_counter,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            }
        except PermissionError as e:
            logger.warning(f"get_project 인증 실패: {e}")
            return {"error": str(e)}
        except Exception:
            logger.error(f"get_project 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}


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
            proj_uuid = uuid.UUID(project_id)

            data = TaskCreate(
                title=title,
                description=description or None,
                priority=priority,
                assignee_id=uuid.UUID(assignee_id) if assignee_id else None,
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
        except Exception:
            logger.error(f"create_task 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}


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
            task_uuid = uuid.UUID(task_id)

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
                update_kwargs["assignee_id"] = uuid.UUID(assignee_id)

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
        except Exception:
            logger.error(f"update_task 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}


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
            task_uuid = uuid.UUID(task_id)
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
        except Exception:
            logger.error(f"get_task 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}


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
            proj_uuid = uuid.UUID(project_id)

            status_filter = TaskStatus(status) if status else None
            assignee_uuid = uuid.UUID(assignee_id) if assignee_id else None
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
        except Exception:
            logger.error(f"list_tasks 실패: {traceback.format_exc()}")
            return [{"error": "내부 오류가 발생했습니다."}]


@mcp.tool()
async def add_comment(api_key: str, task_id: str, content: str) -> dict[str, Any]:
    """업무에 댓글을 작성합니다.

    Args:
        api_key: 사용자 API 키.
        task_id: 업무 UUID 문자열.
        content: 댓글 내용.

    Returns:
        생성된 댓글 정보 딕셔너리.
    """
    from jongji.schemas.comment import CommentCreate
    from jongji.services import comment_service

    async with _session_factory() as db:
        try:
            user = await _require_user(api_key, db)
            task_uuid = uuid.UUID(task_id)
            data = CommentCreate(content=content)
            comment = await comment_service.create_comment(task_uuid, user.id, data, db)
            await db.commit()
            return {
                "id": str(comment.id),
                "task_id": str(comment.task_id),
                "user_id": str(comment.user_id),
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
            }
        except PermissionError as e:
            logger.warning(f"add_comment 인증 실패: {e}")
            return {"error": str(e)}
        except Exception:
            logger.error(f"add_comment 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}


@mcp.tool()
async def search_tasks(
    api_key: str,
    query: str,
    project_id: str = "",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """업무 전문 검색을 수행합니다.

    Args:
        api_key: 사용자 API 키.
        query: 검색어.
        project_id: 프로젝트 UUID 필터 (비어 있으면 전체).
        limit: 최대 결과 수 (기본값 20).

    Returns:
        검색 결과 딕셔너리 목록.
    """
    from jongji.services import search_service

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            proj_uuid = uuid.UUID(project_id) if project_id else None
            response = await search_service.search(
                query,
                project_id=proj_uuid,
                limit=limit,
                db=db,
            )
            return [
                {
                    "type": item.type,
                    "task_id": str(item.task_id),
                    "task_number": item.task_number,
                    "task_title": item.task_title,
                    "project_key": item.project_key,
                    "highlight": item.highlight,
                    "score": item.score,
                }
                for item in response.items
            ]
        except PermissionError as e:
            logger.warning(f"search_tasks 인증 실패: {e}")
            return [{"error": str(e)}]
        except Exception:
            logger.error(f"search_tasks 실패: {traceback.format_exc()}")
            return [{"error": "내부 오류가 발생했습니다."}]


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
            task_uuid = uuid.UUID(task_id)
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
        except Exception:
            logger.error(f"get_task_history 실패: {traceback.format_exc()}")
            return [{"error": "내부 오류가 발생했습니다."}]


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
            proj_uuid = uuid.UUID(project_id)
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
        except Exception:
            logger.error(f"list_labels 실패: {traceback.format_exc()}")
            return [{"error": "내부 오류가 발생했습니다."}]


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
            task_uuid = uuid.UUID(task_id)
            label_uuid = uuid.UUID(label_id)

            # 이미 추가된 라벨인지 확인
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
        except Exception:
            logger.error(f"add_label 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}


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
    from sqlalchemy import delete

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            task_uuid = uuid.UUID(task_id)
            label_uuid = uuid.UUID(label_id)

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
        except Exception:
            logger.error(f"remove_label 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}


@mcp.tool()
async def export_project(
    api_key: str,
    project_id: str,
    output_format: str = "json",
) -> dict[str, Any] | str:
    """프로젝트를 JSON 또는 Markdown 형식으로 내보냅니다.

    Args:
        api_key: 사용자 API 키.
        project_id: 프로젝트 UUID 문자열.
        output_format: 출력 형식 ("json" 또는 "markdown"), 기본값 "json".

    Returns:
        output_format="json"이면 dict, output_format="markdown"이면 str.
    """
    from jongji.services import export_service

    async with _session_factory() as db:
        try:
            await _require_user(api_key, db)
            proj_uuid = uuid.UUID(project_id)
            return await export_service.export_project(proj_uuid, output_format, db)
        except PermissionError as e:
            logger.warning(f"export_project 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            return {"error": str(e)}
        except Exception:
            logger.error(f"export_project 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}


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
            task_uuid = uuid.UUID(task_id)
            return await export_service.export_task(task_uuid, output_format, db)
        except PermissionError as e:
            logger.warning(f"export_task 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            return {"error": str(e)}
        except Exception:
            logger.error(f"export_task 실패: {traceback.format_exc()}")
            return {"error": "내부 오류가 발생했습니다."}
