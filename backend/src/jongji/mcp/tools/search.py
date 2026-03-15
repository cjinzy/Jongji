"""MCP 검색 관련 도구 모듈.

업무 전문 검색 도구를 제공합니다.
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
            proj_uuid = validate_uuid(project_id, "project_id") if project_id else None
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
        except ValueError as e:
            logger.warning(f"search_tasks 입력 검증 실패: {e}")
            return [{"error": str(e)}]
        except Exception as e:
            return [_handle_tool_error("search_tasks", e)]
