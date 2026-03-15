"""MCP 프로젝트 관련 도구 모듈.

프로젝트 목록 조회, 상세 조회, 내보내기 도구를 제공합니다.
"""

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from jongji.mcp.tools.common import (
    _handle_tool_error,
    _require_user,
    _session_factory,
    mcp,
    validate_uuid,
)


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
            team_uuid = validate_uuid(team_id, "team_id")
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
        except ValueError as e:
            logger.warning(f"list_projects 입력 검증 실패: {e}")
            return [{"error": str(e)}]
        except SQLAlchemyError:
            return [_handle_tool_error("list_projects", SQLAlchemyError())]
        except Exception as e:
            return [_handle_tool_error("list_projects", e)]


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
            proj_uuid = validate_uuid(project_id, "project_id")
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
        except ValueError as e:
            logger.warning(f"get_project 입력 검증 실패: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            return _handle_tool_error("get_project", e)
        except Exception as e:
            return _handle_tool_error("get_project", e)


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
            proj_uuid = validate_uuid(project_id, "project_id")
            return await export_service.export_project(proj_uuid, output_format, db)
        except PermissionError as e:
            logger.warning(f"export_project 인증 실패: {e}")
            return {"error": str(e)}
        except ValueError as e:
            logger.warning(f"export_project 입력 검증 실패: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            return _handle_tool_error("export_project", e)
        except Exception as e:
            return _handle_tool_error("export_project", e)
