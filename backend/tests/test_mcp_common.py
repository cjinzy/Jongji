"""MCP common 모듈 테스트.

validate_uuid 유틸리티와 _handle_tool_error 헬퍼를 검증합니다.
"""

import uuid

import pytest

from jongji.mcp.tools.common import _handle_tool_error, validate_uuid


class TestValidateUuid:
    """validate_uuid 함수 테스트."""

    def test_valid_uuid_v4(self):
        """유효한 UUID v4 문자열을 정상 변환합니다."""
        raw = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_uuid(raw, "test_field")
        assert isinstance(result, uuid.UUID)
        assert str(result) == raw

    def test_valid_uuid_without_hyphens(self):
        """하이픈 없는 UUID 문자열도 정상 변환합니다."""
        raw = "550e8400e29b41d4a716446655440000"
        result = validate_uuid(raw, "test_field")
        assert isinstance(result, uuid.UUID)

    def test_invalid_uuid_raises_value_error(self):
        """잘못된 UUID 문자열은 ValueError를 발생시킵니다."""
        with pytest.raises(ValueError, match="test_field"):
            validate_uuid("not-a-uuid", "test_field")

    def test_empty_string_raises_value_error(self):
        """빈 문자열은 ValueError를 발생시킵니다."""
        with pytest.raises(ValueError, match="empty_field"):
            validate_uuid("", "empty_field")

    def test_error_message_contains_field_name(self):
        """에러 메시지에 필드 이름이 포함됩니다."""
        with pytest.raises(ValueError, match="my_field"):
            validate_uuid("bad", "my_field")

    def test_error_message_contains_invalid_value(self):
        """에러 메시지에 잘못된 값이 포함됩니다."""
        with pytest.raises(ValueError, match="xyz123"):
            validate_uuid("xyz123", "some_field")

    def test_random_uuid_roundtrip(self):
        """임의 생성 UUID의 왕복 변환이 동일합니다."""
        original = uuid.uuid4()
        result = validate_uuid(str(original), "round_trip")
        assert result == original


class TestHandleToolError:
    """_handle_tool_error 함수 테스트."""

    def test_returns_error_dict(self):
        """에러 딕셔너리를 반환합니다."""
        result = _handle_tool_error("test_tool", RuntimeError("boom"))
        assert "error" in result
        assert result["error"] == "내부 오류가 발생했습니다."


class TestPackageReexport:
    """패키지 re-export 호환성 테스트."""

    def test_mcp_importable_from_package(self):
        """from jongji.mcp.tools import mcp 가 정상 동작합니다."""
        from jongji.mcp.tools import mcp

        assert mcp is not None

    def test_validate_uuid_importable_from_package(self):
        """from jongji.mcp.tools import validate_uuid 가 정상 동작합니다."""
        from jongji.mcp.tools import validate_uuid as vu

        assert callable(vu)

    def test_mcp_identity(self):
        """common.mcp와 __init__.mcp가 동일 객체입니다."""
        from jongji.mcp.tools import mcp as pkg_mcp
        from jongji.mcp.tools.common import mcp as common_mcp

        assert pkg_mcp is common_mcp
