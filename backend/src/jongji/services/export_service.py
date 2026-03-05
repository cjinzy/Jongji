"""Export 서비스 모듈.

프로젝트 및 업무를 JSON 또는 Markdown 형식으로 내보냅니다.
"""

import traceback
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from jongji.models.label import Label
from jongji.models.task import Task, TaskLabel


async def export_project(
    project_id: uuid.UUID,
    output_format: str,
    db: AsyncSession,
) -> dict | str:
    """프로젝트를 JSON 또는 Markdown 형식으로 내보냅니다.

    Args:
        project_id: 프로젝트 UUID.
        format: 출력 형식 ("json" 또는 "markdown").
        db: 비동기 DB 세션.

    Returns:
        format="json"이면 dict, format="markdown"이면 str.

    Raises:
        ValueError: 프로젝트를 찾을 수 없거나 format이 유효하지 않은 경우.
    """
    from jongji.models.project import Project

    try:
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise ValueError("프로젝트를 찾을 수 없습니다.")

        if output_format not in ("json", "markdown"):
            raise ValueError("output_format은 'json' 또는 'markdown'이어야 합니다.")

        # 라벨 조회
        labels_result = await db.execute(
            select(Label).where(Label.project_id == project_id)
        )
        labels = list(labels_result.scalars().all())

        # 업무 목록 조회 (라벨 + 댓글 + 이력 포함)
        tasks_result = await db.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .options(
                selectinload(Task.labels).joinedload(TaskLabel.label),
                selectinload(Task.comments),
                selectinload(Task.history),
            )
            .order_by(Task.number.asc())
        )
        tasks = list(tasks_result.unique().scalars().all())

        if output_format == "json":
            return _project_to_json(project, tasks, labels)
        return _project_to_markdown(project, tasks, labels)

    except ValueError:
        raise
    except Exception:
        logger.error(f"프로젝트 export 실패: {traceback.format_exc()}")
        raise


async def export_task(
    task_id: uuid.UUID,
    output_format: str,
    db: AsyncSession,
) -> dict | str:
    """업무를 JSON 또는 Markdown 형식으로 내보냅니다.

    Args:
        task_id: 업무 UUID.
        format: 출력 형식 ("json" 또는 "markdown").
        db: 비동기 DB 세션.

    Returns:
        format="json"이면 dict, format="markdown"이면 str.

    Raises:
        ValueError: 업무를 찾을 수 없거나 format이 유효하지 않은 경우.
    """
    try:
        if output_format not in ("json", "markdown"):
            raise ValueError("output_format은 'json' 또는 'markdown'이어야 합니다.")

        task_result = await db.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.labels).joinedload(TaskLabel.label),
                selectinload(Task.comments),
                selectinload(Task.history),
                joinedload(Task.project),
            )
        )
        task = task_result.unique().scalar_one_or_none()
        if not task:
            raise ValueError("업무를 찾을 수 없습니다.")

        if output_format == "json":
            return _task_to_json(task)
        return _task_to_markdown(task)

    except ValueError:
        raise
    except Exception:
        logger.error(f"업무 export 실패: {traceback.format_exc()}")
        raise


def _project_to_json(project, tasks: list, labels: list) -> dict:
    """프로젝트를 JSON 딕셔너리로 변환합니다.

    Args:
        project: Project 모델.
        tasks: Task 목록.
        labels: Label 목록.

    Returns:
        직렬화 가능한 딕셔너리.
    """
    return {
        "id": str(project.id),
        "name": project.name,
        "key": project.key,
        "description": project.description,
        "is_private": project.is_private,
        "is_archived": project.is_archived,
        "owner_id": str(project.owner_id),
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "labels": [
            {
                "id": str(lbl.id),
                "name": lbl.name,
                "color": lbl.color,
            }
            for lbl in labels
        ],
        "tasks": [_task_to_json(t) for t in tasks],
    }


def _task_to_json(task) -> dict:
    """업무를 JSON 딕셔너리로 변환합니다.

    Args:
        task: Task 모델 (labels, comments, history 로드 필요).

    Returns:
        직렬화 가능한 딕셔너리.
    """
    labels = []
    for tl in task.labels:
        label = getattr(tl, "label", None)
        labels.append({
            "label_id": str(tl.label_id),
            "name": label.name if label else None,
            "color": label.color if label else None,
        })

    comments = []
    for c in getattr(task, "comments", []):
        comments.append({
            "id": str(c.id),
            "user_id": str(c.user_id),
            "content": c.content,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        })

    history = []
    for h in getattr(task, "history", []):
        history.append({
            "id": str(h.id),
            "user_id": str(h.user_id),
            "field": h.field,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "created_at": h.created_at.isoformat(),
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
        "comments": comments,
        "history": history,
    }


def _project_to_markdown(project, tasks: list, labels: list) -> str:
    """프로젝트를 Markdown 문자열로 변환합니다.

    Args:
        project: Project 모델.
        tasks: Task 목록.
        labels: Label 목록.

    Returns:
        Markdown 형식 문자열.
    """
    lines = [
        f"# {project.name} ({project.key})",
        "",
    ]
    if project.description:
        lines += [project.description, ""]

    lines += [
        f"- **ID**: {project.id}",
        f"- **비공개**: {'예' if project.is_private else '아니오'}",
        f"- **생성일**: {project.created_at.isoformat()}",
        "",
    ]

    if labels:
        lines += ["## 라벨", ""]
        for lbl in labels:
            color_info = f" (#{lbl.color})" if lbl.color else ""
            lines.append(f"- {lbl.name}{color_info}")
        lines.append("")

    lines += [f"## 업무 목록 ({len(tasks)}개)", ""]
    for task in tasks:
        status = task.status.value if hasattr(task.status, "value") else task.status
        lines.append(f"### [{project.key}-{task.number}] {task.title}")
        lines += [
            "",
            f"- **상태**: {status}",
            f"- **우선순위**: {task.priority}",
        ]
        if task.assignee_id:
            lines.append(f"- **담당자**: {task.assignee_id}")
        if task.due_date:
            lines.append(f"- **마감일**: {task.due_date}")
        if task.description:
            lines += ["", task.description]

        task_labels = [
            tl.label.name for tl in task.labels if getattr(tl, "label", None)
        ]
        if task_labels:
            lines.append(f"- **라벨**: {', '.join(task_labels)}")

        comments = getattr(task, "comments", [])
        if comments:
            lines += ["", f"#### 댓글 ({len(comments)}개)", ""]
            for c in comments:
                lines.append(f"> {c.created_at.strftime('%Y-%m-%d')} - {c.content}")

        lines.append("")

    return "\n".join(lines)


def _task_to_markdown(task) -> str:
    """업무를 Markdown 문자열로 변환합니다.

    Args:
        task: Task 모델 (labels, comments, history 로드 필요).

    Returns:
        Markdown 형식 문자열.
    """
    project_key = ""
    if hasattr(task, "project") and task.project:
        project_key = task.project.key

    status = task.status.value if hasattr(task.status, "value") else task.status
    lines = [
        f"# [{project_key}-{task.number}] {task.title}",
        "",
        f"- **상태**: {status}",
        f"- **우선순위**: {task.priority}",
        f"- **생성자**: {task.creator_id}",
    ]

    if task.assignee_id:
        lines.append(f"- **담당자**: {task.assignee_id}")
    if task.start_date:
        lines.append(f"- **시작일**: {task.start_date}")
    if task.due_date:
        lines.append(f"- **마감일**: {task.due_date}")

    task_labels = [tl.label.name for tl in task.labels if getattr(tl, "label", None)]
    if task_labels:
        lines.append(f"- **라벨**: {', '.join(task_labels)}")

    lines += [
        f"- **생성일**: {task.created_at.isoformat()}",
        f"- **수정일**: {task.updated_at.isoformat()}",
        "",
    ]

    if task.description:
        lines += ["## 설명", "", task.description, ""]

    comments = getattr(task, "comments", [])
    if comments:
        lines += [f"## 댓글 ({len(comments)}개)", ""]
        for c in comments:
            lines.append(f"**{c.created_at.strftime('%Y-%m-%d %H:%M')}** (user: {c.user_id})")
            lines += ["", c.content, ""]

    history = getattr(task, "history", [])
    if history:
        lines += [f"## 변경 이력 ({len(history)}개)", ""]
        for h in history:
            lines.append(
                f"- {h.created_at.strftime('%Y-%m-%d %H:%M')} | **{h.field}**: "
                f"`{h.old_value}` → `{h.new_value}`"
            )
        lines.append("")

    return "\n".join(lines)
