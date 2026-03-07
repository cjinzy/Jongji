"""crypto.py Fernet 암호화 유틸리티 단위 테스트."""

from cryptography.fernet import InvalidToken

from jongji.services.crypto import decrypt_value, encrypt_value, mask_secret


class TestEncryptDecrypt:
    """암호화/복호화 라운드트립 테스트."""

    def test_encrypt_decrypt_roundtrip(self):
        """암호화 후 복호화 시 원문과 일치."""
        plaintext = "my-super-secret-value"
        ciphertext = encrypt_value(plaintext)
        result = decrypt_value(ciphertext)
        assert result == plaintext

    def test_decrypt_invalid_ciphertext(self):
        """잘못된 ciphertext 복호화 시 InvalidToken 발생."""
        import pytest

        with pytest.raises(InvalidToken):
            decrypt_value("this-is-not-valid-fernet-token")

    def test_same_input_different_output(self):
        """동일 입력이 매번 다른 ciphertext를 생성 (Fernet timestamp + random IV)."""
        plaintext = "same-input"
        c1 = encrypt_value(plaintext)
        c2 = encrypt_value(plaintext)
        assert c1 != c2
        # 복호화 결과는 동일해야 함
        assert decrypt_value(c1) == decrypt_value(c2) == plaintext

    def test_encrypt_empty_string(self):
        """빈 문자열도 암호화/복호화 가능."""
        ciphertext = encrypt_value("")
        assert decrypt_value(ciphertext) == ""

    def test_encrypt_unicode(self):
        """유니코드 문자열 암호화/복호화."""
        plaintext = "한글 시크릿 값 🔑"
        assert decrypt_value(encrypt_value(plaintext)) == plaintext


class TestMaskSecret:
    """mask_secret 함수 테스트."""

    def test_mask_long_string(self):
        """긴 문자열: '****' + 마지막 4자 형태 반환."""
        result = mask_secret("secret-api-key-12345")
        assert result == "****2345"

    def test_mask_short_string(self):
        """4자 이하 문자열: '****' 반환."""
        assert mask_secret("ab") == "****"
        assert mask_secret("abc") == "****"
        assert mask_secret("abcd") == "****"

    def test_mask_exactly_tail_chars(self):
        """tail_chars와 동일한 길이: '****' 반환."""
        result = mask_secret("1234", tail_chars=4)
        assert result == "****"

    def test_mask_custom_tail_chars(self):
        """tail_chars 커스텀 설정."""
        result = mask_secret("abcdefgh", tail_chars=2)
        assert result == "****gh"

    def test_mask_empty_string(self):
        """빈 문자열: '****' 반환."""
        assert mask_secret("") == "****"
