"""공통 스키마 모듈.

RFC 7807 Problem Details 에러 응답과 커서 기반 페이지네이션을 정의합니다.
"""

from typing import Any

from pydantic import BaseModel


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details 에러 응답 스키마.

    Attributes:
        type: 에러 타입 URI.
        title: 에러 제목.
        status: HTTP 상태 코드.
        detail: 상세 에러 설명.
        errors: 필드별 에러 목록 (유효성 검증 등).
    """

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    errors: list[dict[str, Any]] | None = None


class CursorPage[T](BaseModel):
    """커서 기반 페이지네이션 응답 스키마.

    Attributes:
        items: 결과 항목 목록.
        next_cursor: 다음 페이지 커서.
        has_more: 추가 데이터 존재 여부.
    """

    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
