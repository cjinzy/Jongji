"""파일 저장소 추상화 모듈.

로컬 디스크 및 S3 저장소 백엔드를 제공하며,
settings.STORAGE_BACKEND 설정에 따라 적절한 구현체를 반환합니다.
"""

import traceback
from abc import ABC, abstractmethod
from pathlib import Path

from loguru import logger


class StorageBackend(ABC):
    """파일 저장소 추상 기반 클래스.

    저장, 삭제, URL 조회 인터페이스를 정의합니다.
    """

    @abstractmethod
    async def save(self, file_bytes: bytes, path: str) -> str:
        """파일을 저장하고 저장 경로를 반환합니다.

        Args:
            file_bytes: 저장할 파일 바이트.
            path: 저장 경로 (상대 경로).

        Returns:
            저장된 파일의 경로 문자열.
        """

    @abstractmethod
    async def delete(self, path: str) -> None:
        """경로에 해당하는 파일을 삭제합니다.

        Args:
            path: 삭제할 파일 경로.
        """

    @abstractmethod
    def get_url(self, path: str) -> str:
        """파일 접근 URL을 반환합니다.

        Args:
            path: 파일 저장 경로.

        Returns:
            파일 접근 URL.
        """


class LocalStorage(StorageBackend):
    """로컬 디스크 저장소.

    settings.UPLOAD_DIR 디렉토리 아래에 파일을 저장합니다.
    """

    def __init__(self, upload_dir: str) -> None:
        """LocalStorage 초기화.

        Args:
            upload_dir: 파일을 저장할 기본 디렉토리 경로.
        """
        self._base = Path(upload_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, path: str) -> str:
        """파일을 로컬 디스크에 저장합니다.

        Args:
            file_bytes: 저장할 파일 바이트.
            path: 저장 경로 (upload_dir 기준 상대 경로).

        Returns:
            저장된 파일의 경로 문자열.
        """
        try:
            dest = self._base / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(file_bytes)
            logger.info(f"파일 저장 완료: {dest}")
            return str(dest)
        except Exception:
            logger.error(f"파일 저장 실패: {traceback.format_exc()}")
            raise

    async def delete(self, path: str) -> None:
        """로컬 파일을 삭제합니다.

        Args:
            path: 삭제할 파일의 절대 또는 상대 경로.
        """
        try:
            target = Path(path)
            if not target.is_absolute():
                target = self._base / path
            if target.exists():
                target.unlink()
                logger.info(f"파일 삭제 완료: {target}")
        except Exception:
            logger.error(f"파일 삭제 실패: {traceback.format_exc()}")
            raise

    def get_url(self, path: str) -> str:
        """로컬 파일 경로를 URL 형태로 반환합니다.

        Args:
            path: 파일 저장 경로.

        Returns:
            /uploads/{path} 형태의 URL.
        """
        return f"/uploads/{path}"


class S3Storage(StorageBackend):
    """AWS S3 저장소.

    boto3 비동기 래퍼(aioboto3)를 사용하여 S3에 파일을 저장합니다.
    """

    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str) -> None:
        """S3Storage 초기화.

        Args:
            bucket: S3 버킷 이름.
            region: AWS 리전.
            access_key: AWS 액세스 키.
            secret_key: AWS 시크릿 키.
        """
        self._bucket = bucket
        self._region = region
        self._access_key = access_key
        self._secret_key = secret_key

    async def save(self, file_bytes: bytes, path: str) -> str:
        """파일을 S3에 업로드합니다.

        Args:
            file_bytes: 저장할 파일 바이트.
            path: S3 오브젝트 키.

        Returns:
            저장된 S3 오브젝트 키.
        """
        try:
            import aioboto3  # type: ignore[import-untyped]

            session = aioboto3.Session(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region,
            )
            async with session.client("s3") as s3:
                await s3.put_object(Bucket=self._bucket, Key=path, Body=file_bytes)
            logger.info(f"S3 업로드 완료: s3://{self._bucket}/{path}")
            return path
        except Exception:
            logger.error(f"S3 업로드 실패: {traceback.format_exc()}")
            raise

    async def delete(self, path: str) -> None:
        """S3 오브젝트를 삭제합니다.

        Args:
            path: 삭제할 S3 오브젝트 키.
        """
        try:
            import aioboto3  # type: ignore[import-untyped]

            session = aioboto3.Session(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region,
            )
            async with session.client("s3") as s3:
                await s3.delete_object(Bucket=self._bucket, Key=path)
            logger.info(f"S3 삭제 완료: s3://{self._bucket}/{path}")
        except Exception:
            logger.error(f"S3 삭제 실패: {traceback.format_exc()}")
            raise

    def get_url(self, path: str) -> str:
        """S3 오브젝트 공개 URL을 반환합니다.

        Args:
            path: S3 오브젝트 키.

        Returns:
            S3 공개 URL.
        """
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{path}"


def get_storage() -> StorageBackend:
    """설정에 따라 적절한 StorageBackend 인스턴스를 반환합니다.

    settings.STORAGE_BACKEND가 "s3"이면 S3Storage를,
    그 외에는 LocalStorage를 반환합니다.

    Returns:
        StorageBackend 구현체.
    """
    from jongji.config import settings  # 순환 import 방지용 지연 import

    backend = getattr(settings, "STORAGE_BACKEND", "local")
    if backend == "s3":
        return S3Storage(
            bucket=getattr(settings, "S3_BUCKET", ""),
            region=getattr(settings, "S3_REGION", "ap-northeast-2"),
            access_key=getattr(settings, "S3_ACCESS_KEY", ""),
            secret_key=getattr(settings, "S3_SECRET_KEY", ""),
        )
    upload_dir = getattr(settings, "UPLOAD_DIR", "./uploads")
    return LocalStorage(upload_dir=upload_dir)
