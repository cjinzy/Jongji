"""Dashboard API 엔드포인트.

프로젝트 대시보드 집계 데이터를 실시간 SQL 쿼리로 반환합니다.
"""

import traceback
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import require_project_access
from jongji.database import get_db
from jongji.models.enums import TaskStatus
from jongji.models.label import Label
from jongji.models.project import Project
from jongji.models.task import Task, TaskLabel
from jongji.models.user import User
from jongji.schemas.dashboard import (
    AssigneeWorkloadItem,
    DailyCountItem,
    DashboardResponse,
    LabelDistributionItem,
    PriorityDistributionItem,
)
from jongji.utils.cache import dashboard_cache

router = APIRouter(tags=["dashboard"])

_COMPLETED_STATUSES = {TaskStatus.DONE, TaskStatus.CLOSED}


@router.get("/api/v1/projects/{project_id}/dashboard")
async def get_dashboard(
    project_id: uuid.UUID,
    user: User = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """프로젝트 대시보드 집계 데이터를 반환합니다.

    상태별/우선순위별/담당자별 업무 수, 최근 30일 일별 생성·완료 업무 수,
    라벨별 업무 수, 전체·완료 업무 수 및 완료율을 실시간으로 집계합니다.

    Args:
        project_id: 프로젝트 UUID.
        user: 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        DashboardResponse: 대시보드 집계 데이터.

    Raises:
        HTTPException 404: 프로젝트 미존재.
        HTTPException 500: 집계 쿼리 실패.
    """
    # 캐시 조회
    cache_key = f"dashboard:{project_id}"
    cached = await dashboard_cache.get(cache_key)
    if cached:
        return cached

    # 프로젝트 존재 여부 확인
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="프로젝트를 찾을 수 없습니다.")

    try:
        # 1. 상태별 업무 수
        status_rows = await db.execute(
            select(Task.status, func.count(Task.id).label("cnt"))
            .where(Task.project_id == project_id, Task.is_archived.is_(False))
            .group_by(Task.status)
        )
        status_counts: dict[str, int] = {s.value: 0 for s in TaskStatus}
        for row in status_rows:
            status_counts[str(row.status)] = row.cnt

        # 2. 우선순위별 업무 수
        priority_rows = await db.execute(
            select(Task.priority, func.count(Task.id).label("cnt"))
            .where(Task.project_id == project_id, Task.is_archived.is_(False))
            .group_by(Task.priority)
            .order_by(Task.priority)
        )
        priority_distribution = [
            PriorityDistributionItem(priority=row.priority, count=row.cnt)
            for row in priority_rows
        ]

        # 3. 담당자별 미완료 업무 수
        workload_rows = await db.execute(
            select(User.id, User.name, func.count(Task.id).label("cnt"))
            .join(Task, Task.assignee_id == User.id)
            .where(
                Task.project_id == project_id,
                Task.is_archived.is_(False),
                Task.status.notin_([TaskStatus.DONE, TaskStatus.CLOSED]),
            )
            .group_by(User.id, User.name)
            .order_by(func.count(Task.id).desc())
        )
        assignee_workload = [
            AssigneeWorkloadItem(user_id=row.id, user_name=row.name, count=row.cnt)
            for row in workload_rows
        ]

        # 4. 최근 30일 일별 생성 업무 수
        thirty_days_ago = date.today() - timedelta(days=30)
        created_rows = await db.execute(
            select(
                func.date(Task.created_at).label("day"),
                func.count(Task.id).label("cnt"),
            )
            .where(
                Task.project_id == project_id,
                func.date(Task.created_at) >= thirty_days_ago,
            )
            .group_by(func.date(Task.created_at))
            .order_by(func.date(Task.created_at))
        )
        daily_created = [
            DailyCountItem(date=str(row.day), count=row.cnt)
            for row in created_rows
        ]

        # 5. 최근 30일 일별 완료 업무 수 (DONE 또는 CLOSED 상태로 업데이트된 날짜 기준)
        completed_rows = await db.execute(
            select(
                func.date(Task.updated_at).label("day"),
                func.count(Task.id).label("cnt"),
            )
            .where(
                Task.project_id == project_id,
                Task.status.in_([TaskStatus.DONE, TaskStatus.CLOSED]),
                func.date(Task.updated_at) >= thirty_days_ago,
            )
            .group_by(func.date(Task.updated_at))
            .order_by(func.date(Task.updated_at))
        )
        daily_completed = [
            DailyCountItem(date=str(row.day), count=row.cnt)
            for row in completed_rows
        ]

        # 6. 라벨별 업무 수
        label_rows = await db.execute(
            select(
                Label.id,
                Label.name,
                Label.color,
                func.count(TaskLabel.task_id).label("cnt"),
            )
            .join(TaskLabel, TaskLabel.label_id == Label.id)
            .join(Task, Task.id == TaskLabel.task_id)
            .where(Task.project_id == project_id, Task.is_archived.is_(False))
            .group_by(Label.id, Label.name, Label.color)
            .order_by(func.count(TaskLabel.task_id).desc())
        )
        label_distribution = [
            LabelDistributionItem(
                label_id=row.id,
                label_name=row.name,
                color=row.color,
                count=row.cnt,
            )
            for row in label_rows
        ]

        # 7. 전체/완료 업무 수 및 완료율
        total_result = await db.execute(
            select(func.count(Task.id))
            .where(Task.project_id == project_id, Task.is_archived.is_(False))
        )
        total_tasks: int = total_result.scalar_one() or 0

        completed_result = await db.execute(
            select(func.count(Task.id))
            .where(
                Task.project_id == project_id,
                Task.is_archived.is_(False),
                Task.status.in_([TaskStatus.DONE, TaskStatus.CLOSED]),
            )
        )
        completed_tasks: int = completed_result.scalar_one() or 0

        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0

        logger.info(f"대시보드 집계 완료: project={project_id}, total={total_tasks}, completed={completed_tasks}")

        response = DashboardResponse(
            status_counts=status_counts,
            priority_distribution=priority_distribution,
            assignee_workload=assignee_workload,
            daily_created=daily_created,
            daily_completed=daily_completed,
            label_distribution=label_distribution,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            completion_rate=completion_rate,
        )
        await dashboard_cache.set(cache_key, response)
        return response

    except HTTPException:
        raise
    except Exception:
        logger.error(f"대시보드 집계 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대시보드 데이터를 가져오는 데 실패했습니다.",
        )
