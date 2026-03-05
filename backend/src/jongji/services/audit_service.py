"""감사 로그 서비스 레이어.

사용자 행동을 audit_logs 테이블에 기록하고 조회하는 비즈니스 로직을 처리합니다.
"""

import traceback
import uuid
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.audit import AuditLog
from jongji.models.enums import AuditLogLevel


async def log_action(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
    source: str = "api",
    ip_address: str | None = None,
    log_level: AuditLogLevel = AuditLogLevel.STANDARD,
) -> AuditLog:
    """사용자 행동을 감사 로그에 기록합니다.

    Args:
        db: 비동기 DB 세션.
        user_id: 행위자 사용자 UUID (익명이면 None).
        action: 수행된 액션 문자열 (예: "task.create").
        resource_type: 리소스 유형 (예: "task").
        resource_id: 대상 리소스 UUID.
        detail: 추가 상세 정보.
        source: 요청 출처 ("api" | "mcp").
        ip_address: 클라이언트 IP 주소.

    Returns:
        생성된 AuditLog 인스턴스.
    """
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=detail,
            source=source,
            ip_address=ip_address,
            log_level=log_level,
        )
        db.add(log)
        await db.flush()
        logger.debug(f"감사 로그 기록: action={action}, resource_type={resource_type}, user_id={user_id}")
        return log
    except Exception:
        logger.error(f"감사 로그 기록 실패:\n{traceback.format_exc()}")
        raise


async def list_audit_logs(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    resource_type: str | None = None,
    user_id: uuid.UUID | None = None,
) -> tuple[list[AuditLog], int]:
    """감사 로그 목록을 페이지네이션으로 조회합니다.

    Args:
        db: 비동기 DB 세션.
        limit: 페이지 크기 (최대 200).
        offset: 오프셋.
        action: 액션 필터.
        resource_type: 리소스 유형 필터.
        user_id: 사용자 UUID 필터.

    Returns:
        (로그 목록, 전체 개수) 튜플.
    """
    try:
        query = select(AuditLog)

        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        logs = list(result.scalars().all())

        return logs, total
    except Exception:
        logger.error(f"감사 로그 조회 실패:\n{traceback.format_exc()}")
        raise
