"""MCP 댓글 관련 도구 모듈.

업무 댓글 작성 도구를 제공합니다.
"""

from typing import Any

from loguru import logger

from jongji.mcp.tools.common import (
    _handle_tool_error,
    _require_user,
    _session_factory,
    mcp,
    validate_uuid,
)


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
            task_uuid = validate_uuid(task_id, "task_id")
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
        except ValueError as e:
            logger.warning(f"add_comment 입력 검증 실패: {e}")
            return {"error": str(e)}
        except Exception as e:
            return _handle_tool_error("add_comment", e)
