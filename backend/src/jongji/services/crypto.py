"""암호화 유틸리티 모듈.

Fernet 대칭 암호화를 사용하여 민감한 설정값(OAuth 클라이언트 시크릿 등)을
안전하게 암호화/복호화합니다.

암호화 키는 애플리케이션의 SECRET_KEY에서 HKDF를 통해 파생되므로,
별도의 암호화 키 관리 없이 기존 비밀 키를 재사용할 수 있습니다.
"""

import base64
import traceback

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from loguru import logger

from jongji.config import settings

# HKDF 파생에 사용할 Salt (고정값; 키 파생 도메인 분리용)
_HKDF_SALT = b"jongji-fernet-salt"
_HKDF_INFO = b"jongji-settings-encryption"


def _derive_fernet_key(secret_key: str | None = None) -> bytes:
    """SECRET_KEY에서 Fernet 호환 32바이트 키를 파생합니다.

    HKDF(HMAC-based Extract-and-Expand Key Derivation Function)를 사용하여
    임의 길이의 SECRET_KEY로부터 Fernet이 요구하는 정확히 32바이트의 키를 파생합니다.

    Args:
        secret_key: 키 파생에 사용할 비밀 키 문자열.
                    None이면 settings.SECRET_KEY를 사용합니다.

    Returns:
        bytes: URL-safe base64로 인코딩된 32바이트 Fernet 키.
    """
    key_material = (secret_key or settings.SECRET_KEY).encode("utf-8")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    )
    raw_key = hkdf.derive(key_material)
    return base64.urlsafe_b64encode(raw_key)


def _get_fernet() -> Fernet:
    """Fernet 인스턴스를 반환합니다.

    매 호출마다 새 인스턴스를 생성합니다 (키는 settings에서 파생되므로 일관됩니다).

    Returns:
        Fernet: 파생된 키로 초기화된 Fernet 인스턴스.
    """
    key = _derive_fernet_key()
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """문자열 값을 Fernet으로 암호화합니다.

    Args:
        plaintext: 암호화할 평문 문자열.

    Returns:
        str: URL-safe base64로 인코딩된 암호문 문자열.

    Raises:
        Exception: 암호화 실패 시 예외를 발생시킵니다.
    """
    try:
        fernet = _get_fernet()
        token = fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")
    except Exception:
        logger.error("암호화 실패:\n{}", traceback.format_exc())
        raise


def decrypt_value(ciphertext: str) -> str:
    """Fernet으로 암호화된 문자열을 복호화합니다.

    Args:
        ciphertext: encrypt_value()로 암호화된 문자열.

    Returns:
        str: 복호화된 평문 문자열.

    Raises:
        InvalidToken: 잘못된 토큰이거나 키가 일치하지 않을 때.
        Exception: 그 외 복호화 실패 시.
    """
    try:
        fernet = _get_fernet()
        plaintext = fernet.decrypt(ciphertext.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken:
        logger.error(
            "복호화 실패 — 토큰이 유효하지 않거나 키가 다릅니다:\n{}",
            traceback.format_exc(),
        )
        raise
    except Exception:
        logger.error("복호화 실패:\n{}", traceback.format_exc())
        raise


def mask_secret(secret: str, tail_chars: int = 4) -> str:
    """민감한 문자열의 일부를 마스킹하여 반환합니다.

    로그 출력이나 API 응답에서 시크릿 값의 끝 일부만 노출할 때 사용합니다.

    Args:
        secret: 마스킹할 원본 문자열.
        tail_chars: 끝에서 노출할 문자 수 (기본값: 4).

    Returns:
        str: "****" + 마지막 tail_chars자 형태의 마스킹된 문자열.
             secret이 tail_chars보다 짧거나 같으면 "****"만 반환합니다.

    Examples:
        >>> mask_secret("secret-api-key-12345")
        '****2345'
        >>> mask_secret("ab")
        '****'
    """
    if len(secret) <= tail_chars:
        return "****"
    return "****" + secret[-tail_chars:]
