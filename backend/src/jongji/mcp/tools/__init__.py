"""MCP Tool 패키지.

도메인별로 분할된 14개의 MCP Tool을 등록하고 공용 객체를 re-export합니다.

하위 모듈:
    - common: FastMCP 인스턴스, DB 세션, 인증 헬퍼, UUID 검증
    - projects: 프로젝트 CRUD / 내보내기
    - tasks: 업무 CRUD / 이력 / 라벨 / 내보내기
    - comments: 댓글 작성
    - search: 업무 전문 검색
"""

# 하위 모듈 import → @mcp.tool() 데코레이터가 실행되어 도구가 등록됨
import jongji.mcp.tools.comments  # noqa: F401
import jongji.mcp.tools.projects  # noqa: F401
import jongji.mcp.tools.search  # noqa: F401
import jongji.mcp.tools.tasks  # noqa: F401

# common에서 공용 객체 re-export (기존 import 호환성 유지)
from jongji.mcp.tools.common import mcp, validate_uuid

__all__ = [
    "mcp",
    "validate_uuid",
]
