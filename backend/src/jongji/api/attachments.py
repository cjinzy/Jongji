"""첨부파일 API 엔드포인트.

업무 첨부, 임시 업로드, 파일 다운로드, 삭제를 제공합니다.
"""

import traceback
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user
from jongji.database import get_db
from jongji.models.attachment import Attachment
from jongji.models.task import Task
from jongji.models.user import User
from jongji.schemas.attachment import AttachmentResponse
from jongji.services.storage import get_storage

router = APIRouter(tags=["attachments"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/json",
}
ALLOWED_PREFIXES = ("image/", "text/")


def _is_allowed_content_type(content_type: str) -> bool:
    """허용된 MIME 타입인지 검사합니다.

    Args:
        content_type: 검사할 MIME 타입 문자열.

    Returns:
        허용 여부.
    """
    if content_type in ALLOWED_CONTENT_TYPES:
        return True
    return any(content_type.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _attachment_to_response(attachment: Attachment) -> AttachmentResponse:
    """Attachment 모델을 AttachmentResponse로 변환합니다.

    Args:
        attachment: Attachment SQLAlchemy 모델.

    Returns:
        AttachmentResponse 스키마.
    """
    return AttachmentResponse(
        id=attachment.id,
        task_id=attachment.task_id,
        comment_id=attachment.comment_id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=attachment.size,
        is_temp=attachment.is_temp,
        created_at=attachment.created_at,
    )


@router.post(
    "/api/v1/tasks/{task_id}/attachments",
    status_code=status.HTTP_201_CREATED,
)
async def upload_task_attachment(
    task_id: uuid.UUID,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttachmentResponse:
    """업무에 파일을 첨부합니다.

    Args:
        task_id: 첨부할 작업 UUID.
        file: 업로드할 파일.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        AttachmentResponse: 생성된 첨부파일 정보.

    Raises:
        HTTPException 404: 작업 미존재.
        HTTPException 413: 파일 크기 초과.
        HTTPException 415: 허용되지 않는 MIME 타입.
    """
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    content_type = file.content_type or "application/octet-stream"
    if not _is_allowed_content_type(content_type):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"허용되지 않는 MIME 타입입니다: {content_type}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="파일 크기는 10MB를 초과할 수 없습니다.",
        )

    try:
        storage = get_storage()
        rel_path = f"tasks/{task_id}/{uuid.uuid4().hex}_{file.filename}"
        saved_path = await storage.save(file_bytes, rel_path)

        attachment = Attachment(
            task_id=task_id,
            filename=file.filename or "",
            storage_path=saved_path,
            content_type=content_type,
            size=len(file_bytes),
            uploaded_by=user.id,
            is_temp=False,
        )
        db.add(attachment)
        await db.flush()
        await db.refresh(attachment)
        await db.commit()
        logger.info(f"작업 첨부파일 업로드 완료: task={task_id}, attachment={attachment.id}")
        return _attachment_to_response(attachment)
    except HTTPException:
        raise
    except Exception:
        logger.error(f"작업 첨부파일 업로드 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 업로드에 실패했습니다.",
        )


@router.post(
    "/api/v1/attachments/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_temp_attachment(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttachmentResponse:
    """에디터 이미지 붙여넣기용 임시 파일을 업로드합니다 (24h TTL).

    Args:
        file: 업로드할 파일.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        AttachmentResponse: 생성된 임시 첨부파일 정보 (is_temp=True).

    Raises:
        HTTPException 413: 파일 크기 초과.
        HTTPException 415: 허용되지 않는 MIME 타입.
    """
    content_type = file.content_type or "application/octet-stream"
    if not _is_allowed_content_type(content_type):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"허용되지 않는 MIME 타입입니다: {content_type}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="파일 크기는 10MB를 초과할 수 없습니다.",
        )

    try:
        storage = get_storage()
        rel_path = f"temp/{user.id}/{uuid.uuid4().hex}_{file.filename}"
        saved_path = await storage.save(file_bytes, rel_path)

        attachment = Attachment(
            task_id=None,
            filename=file.filename or "",
            storage_path=saved_path,
            content_type=content_type,
            size=len(file_bytes),
            uploaded_by=user.id,
            is_temp=True,
        )
        db.add(attachment)
        await db.flush()
        await db.refresh(attachment)
        await db.commit()
        logger.info(f"임시 파일 업로드 완료: attachment={attachment.id}, user={user.id}")
        return _attachment_to_response(attachment)
    except HTTPException:
        raise
    except Exception:
        logger.error(f"임시 파일 업로드 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 업로드에 실패했습니다.",
        )


@router.get("/api/v1/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """첨부파일을 다운로드합니다.

    Args:
        attachment_id: 첨부파일 UUID.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        FileResponse: 파일 스트림 응답.

    Raises:
        HTTPException 404: 첨부파일 미존재 또는 파일 없음.
    """
    result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부파일을 찾을 수 없습니다.")

    file_path = Path(attachment.storage_path)
    if not file_path.is_absolute():
        from jongji.config import settings

        upload_dir = getattr(settings, "UPLOAD_DIR", "./uploads")
        file_path = Path(upload_dir) / attachment.storage_path

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="파일을 찾을 수 없습니다.")

    return FileResponse(
        path=str(file_path),
        filename=attachment.filename,
        media_type=attachment.content_type,
    )


@router.delete("/api/v1/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """첨부파일을 삭제합니다. 업로더만 삭제 가능합니다.

    Args:
        attachment_id: 첨부파일 UUID.
        user: 인증된 사용자.
        db: DB 세션.

    Raises:
        HTTPException 404: 첨부파일 미존재.
        HTTPException 403: 업로더가 아닌 경우.
    """
    result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부파일을 찾을 수 없습니다.")

    if attachment.uploaded_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인이 업로드한 파일만 삭제할 수 있습니다.",
        )

    try:
        storage = get_storage()
        await storage.delete(attachment.storage_path)
        await db.delete(attachment)
        await db.flush()
        await db.commit()
        logger.info(f"첨부파일 삭제 완료: attachment={attachment_id}, user={user.id}")
    except HTTPException:
        raise
    except Exception:
        logger.error(f"첨부파일 삭제 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 삭제에 실패했습니다.",
        )
