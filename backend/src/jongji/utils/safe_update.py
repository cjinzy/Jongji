"""안전한 모델 업데이트 유틸리티."""

import traceback

from loguru import logger


def safe_update(
    instance: object,
    data: dict,
    allowed_fields: frozenset[str],
) -> list[str]:
    """허용된 필드만 모델 인스턴스에 적용합니다.

    허용되지 않은 필드가 data에 포함되면 ValueError를 발생시켜
    Mass Assignment 취약점(H-04)을 방지합니다.

    Args:
        instance: SQLAlchemy 모델 인스턴스.
        data: 업데이트할 {field: value} 딕셔너리.
        allowed_fields: 허용된 필드명 frozenset.

    Returns:
        실제로 변경된 필드명 목록.

    Raises:
        ValueError: 허용되지 않은 필드가 포함된 경우.
    """
    try:
        disallowed = set(data.keys()) - allowed_fields
        if disallowed:
            logger.warning(f"허용되지 않은 필드 수정 시도: {disallowed}")
            raise ValueError(f"수정할 수 없는 필드: {disallowed}")

        changed: list[str] = []
        for field, value in data.items():
            if field in allowed_fields:
                old_value = getattr(instance, field, None)
                if old_value != value:
                    setattr(instance, field, value)
                    changed.append(field)
        return changed
    except ValueError:
        raise
    except Exception:
        logger.error(f"safe_update 실패: {traceback.format_exc()}")
        raise
