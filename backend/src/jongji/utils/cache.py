"""인메모리 TTL 기반 캐시 유틸리티.

단일 서버 환경에서 사용하는 간단한 TTL 캐시입니다.
"""

import asyncio
import time
from typing import Any

from loguru import logger


class TTLCache:
    """TTL 기반 인메모리 캐시.

    Args:
        default_ttl: 기본 캐시 유효 시간(초).
        max_size: 최대 캐시 항목 수.
    """

    def __init__(self, default_ttl: float = 30.0, max_size: int = 256) -> None:
        """캐시 인스턴스를 초기화합니다."""
        self._cache: dict[str, tuple[float, Any]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """캐시에서 값을 조회합니다. 만료되었으면 None을 반환합니다.

        Args:
            key: 캐시 키.

        Returns:
            저장된 값 또는 None(만료/미존재 시).
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            expire_at, value = entry
            if time.monotonic() > expire_at:
                self._cache.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """캐시에 값을 저장합니다.

        Args:
            key: 캐시 키.
            value: 저장할 값.
            ttl: 유효 시간(초). None이면 default_ttl 사용.
        """
        async with self._lock:
            if len(self._cache) >= self._max_size:
                self._evict_expired()
            expire_at = time.monotonic() + (ttl or self._default_ttl)
            self._cache[key] = (expire_at, value)

    def _evict_expired(self) -> None:
        """만료된 항목을 제거합니다."""
        now = time.monotonic()
        expired_keys = [k for k, (exp, _) in self._cache.items() if now > exp]
        for k in expired_keys:
            del self._cache[k]
        logger.debug(f"캐시 만료 항목 제거: {len(expired_keys)}개")

    async def invalidate(self, key: str) -> None:
        """특정 키의 캐시를 무효화합니다.

        Args:
            key: 무효화할 캐시 키.
        """
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """전체 캐시를 초기화합니다."""
        self._cache.clear()


# 전역 대시보드 캐시 인스턴스
dashboard_cache = TTLCache(default_ttl=30.0)
