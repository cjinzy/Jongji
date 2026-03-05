"""SSE(Server-Sent Events) 이벤트 스트리밍 API 모듈.

PostgreSQL LISTEN/NOTIFY 기반 EventBus를 통해 실시간 이벤트를 클라이언트에게 전달합니다.
"""

import traceback
import uuid

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from loguru import logger

from jongji.services.event_bus import event_bus

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/stream")
async def stream_events(
    project_id: uuid.UUID = Query(..., description="구독할 프로젝트 UUID"),
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """프로젝트 이벤트 SSE 스트림 엔드포인트.

    Last-Event-ID 헤더가 있으면 버퍼에서 누락된 이벤트를 재전송합니다.

    Args:
        project_id: 구독할 프로젝트 UUID (쿼리 파라미터).
        last_event_id: 클라이언트의 마지막 수신 이벤트 ID (재연결 지원).

    Returns:
        StreamingResponse: SSE text/event-stream 응답.

    Raises:
        HTTPException: 잘못된 project_id 형식인 경우 400.
    """
    try:
        project_id_str = str(project_id)
        logger.info(f"SSE 스트림 연결 project_id={project_id_str} last_event_id={last_event_id}")

        return StreamingResponse(
            event_bus.subscribe(project_id_str, last_event_id=last_event_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
    except Exception:
        logger.error(f"SSE 스트림 오류 project_id={project_id}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이벤트 스트림 연결에 실패했습니다.",
        )


__all__ = ["router"]
