"""Slug 생성 유틸리티."""

import re
import unicodedata


def generate_slug(name: str) -> str:
    """이름에서 URL-safe slug를 생성합니다.

    한국어/영어 모두 지원합니다. 한국어는 그대로 유지하되
    특수문자와 공백을 하이픈으로 변환합니다.

    Args:
        name: 원본 이름.

    Returns:
        URL-safe slug 문자열.
    """
    # NFD -> NFC 정규화
    slug = unicodedata.normalize("NFC", name.strip().lower())
    # 알파벳, 숫자, 한글, 하이픈만 유지
    slug = re.sub(r"[^a-z0-9가-힣-]", "-", slug)
    # 연속 하이픈 제거
    slug = re.sub(r"-+", "-", slug)
    # 앞뒤 하이픈 제거
    slug = slug.strip("-")
    return slug or "untitled"
