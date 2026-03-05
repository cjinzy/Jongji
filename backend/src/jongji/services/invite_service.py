"""팀 초대 링크 서비스 모듈.

초대 생성, 목록 조회, 비활성화, 토큰을 통한 팀 참여 로직을 담당합니다.
"""

import secrets
import traceback
import uuid
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.enums import TeamRole
from jongji.models.team import TeamInvite, TeamMember


async def create_invite(
    team_id: uuid.UUID,
    created_by: uuid.UUID,
    expires_in_days: int,
    max_uses: int | None,
    db: AsyncSession,
) -> TeamInvite:
    """팀 초대 링크를 생성합니다.

    Args:
        team_id: 초대를 생성할 팀 UUID.
        created_by: 초대를 생성한 사용자 UUID.
        expires_in_days: 초대 링크 유효 기간(일).
        max_uses: 최대 사용 횟수 (None이면 무제한).
        db: 비동기 DB 세션.

    Returns:
        TeamInvite: 생성된 초대 모델.

    Raises:
        Exception: DB 오류 발생 시.
    """
    try:
        invite = TeamInvite(
            id=uuid.uuid4(),
            team_id=team_id,
            created_by=created_by,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
            max_uses=max_uses,
            use_count=0,
            is_active=True,
        )
        db.add(invite)
        await db.flush()
        await db.refresh(invite)
        logger.info(f"팀 초대 생성: team_id={team_id}, invite_id={invite.id}")
        return invite
    except Exception:
        logger.error(f"팀 초대 생성 실패: {traceback.format_exc()}")
        raise


async def list_invites(
    team_id: uuid.UUID,
    db: AsyncSession,
) -> list[TeamInvite]:
    """팀의 활성 초대 링크 목록을 반환합니다.

    Args:
        team_id: 조회할 팀 UUID.
        db: 비동기 DB 세션.

    Returns:
        list[TeamInvite]: 활성 초대 목록.

    Raises:
        Exception: DB 오류 발생 시.
    """
    try:
        result = await db.execute(
            select(TeamInvite).where(
                TeamInvite.team_id == team_id,
                TeamInvite.is_active.is_(True),
            )
        )
        return list(result.scalars().all())
    except Exception:
        logger.error(f"팀 초대 목록 조회 실패: {traceback.format_exc()}")
        raise


async def deactivate_invite(
    invite_id: uuid.UUID,
    team_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """초대 링크를 비활성화합니다.

    Args:
        invite_id: 비활성화할 초대 UUID.
        team_id: 초대가 속한 팀 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 해당 초대를 찾을 수 없을 때.
        Exception: DB 오류 발생 시.
    """
    try:
        result = await db.execute(
            select(TeamInvite).where(
                TeamInvite.id == invite_id,
                TeamInvite.team_id == team_id,
            )
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise ValueError(f"초대를 찾을 수 없습니다: invite_id={invite_id}")
        invite.is_active = False
        await db.flush()
        logger.info(f"팀 초대 비활성화: invite_id={invite_id}")
    except ValueError:
        raise
    except Exception:
        logger.error(f"팀 초대 비활성화 실패: {traceback.format_exc()}")
        raise


async def join_by_token(
    token: str,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> TeamMember:
    """초대 토큰으로 팀에 참여합니다.

    이미 팀 멤버인 경우 멱등성을 보장하여 기존 멤버십을 반환합니다.

    Args:
        token: 초대 토큰 문자열.
        user_id: 참여할 사용자 UUID.
        db: 비동기 DB 세션.

    Returns:
        TeamMember: 생성되거나 기존의 팀 멤버 모델.

    Raises:
        ValueError: 초대 토큰을 찾을 수 없을 때.
        PermissionError: 초대가 만료되었거나 비활성화되었거나 사용 한도를 초과했을 때.
        Exception: DB 오류 발생 시.
    """
    try:
        # 초대 토큰 조회
        result = await db.execute(
            select(TeamInvite).where(TeamInvite.token == token)
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise ValueError(f"초대 토큰을 찾을 수 없습니다: token={token}")

        # 활성 여부 확인
        if not invite.is_active:
            raise PermissionError("비활성화된 초대 링크입니다.")

        # 만료 여부 확인
        if datetime.now(UTC) > invite.expires_at:
            raise PermissionError("만료된 초대 링크입니다.")

        # 최대 사용 횟수 확인
        if invite.max_uses is not None and invite.use_count >= invite.max_uses:
            raise PermissionError("최대 사용 횟수를 초과한 초대 링크입니다.")

        # 이미 멤버인지 확인 (멱등성)
        member_result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == invite.team_id,
                TeamMember.user_id == user_id,
            )
        )
        existing_member = member_result.scalar_one_or_none()
        if existing_member is not None:
            logger.info(f"이미 팀 멤버: team_id={invite.team_id}, user_id={user_id}")
            return existing_member

        # 멤버 추가
        member = TeamMember(
            id=uuid.uuid4(),
            team_id=invite.team_id,
            user_id=user_id,
            role=TeamRole.MEMBER,
        )
        db.add(member)

        # 사용 횟수 증가
        invite.use_count += 1
        await db.flush()
        await db.refresh(member)

        logger.info(f"팀 참여 완료: team_id={invite.team_id}, user_id={user_id}")
        return member
    except (ValueError, PermissionError):
        raise
    except Exception:
        logger.error(f"팀 참여 실패: {traceback.format_exc()}")
        raise
