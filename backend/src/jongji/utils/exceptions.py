"""공용 FastAPI exception handler 모음.

ValueError → 400, PermissionError → 403, 기타 Exception → 500 으로 변환합니다.
API 라우터에서 반복되던 try/except 보일러플레이트를 대체합니다.

단, 다음 경우는 라우터에서 직접 처리합니다:
- HTTPException을 직접 raise하는 경우 (FastAPI가 이미 처리)
- 404 반환이 필요한 경우 (ValueError가 항상 400이 아닌 경우)
- 특수 status code 매핑이 필요한 경우 (예: 401, 409, 423)
"""

import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """ValueError를 HTTP 400 응답으로 변환합니다.

    Args:
        request: HTTP 요청 객체.
        exc: 발생한 ValueError.

    Returns:
        JSONResponse: 400 상태 코드와 에러 메시지.
    """
    logger.warning(
        f"ValueError on {request.method} {request.url.path}: {exc}\n"
        f"{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
    """PermissionError를 HTTP 403 응답으로 변환합니다.

    Args:
        request: HTTP 요청 객체.
        exc: 발생한 PermissionError.

    Returns:
        JSONResponse: 403 상태 코드와 에러 메시지.
    """
    logger.warning(
        f"PermissionError on {request.method} {request.url.path}: {exc}\n"
        f"{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc)},
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """예상치 못한 예외를 HTTP 500 응답으로 변환합니다.

    HTTPException은 FastAPI가 먼저 처리하므로 여기까지 도달하지 않습니다.

    Args:
        request: HTTP 요청 객체.
        exc: 발생한 예외.

    Returns:
        JSONResponse: 500 상태 코드와 일반 에러 메시지.
    """
    logger.error(
        f"Unhandled error on {request.method} {request.url.path}: {type(exc).__name__}: {exc}\n"
        f"{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
