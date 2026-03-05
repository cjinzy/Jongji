"""MCP Tool 등록 테스트.

FastMCP 인스턴스에 14개 Tool이 정상 등록되었는지 확인합니다.
개별 Tool의 비즈니스 로직은 services 계층 테스트 및 API 테스트에서 커버됩니다.
"""

from jongji.mcp.tools import mcp

EXPECTED_TOOLS = {
    "list_projects",
    "get_project",
    "create_task",
    "update_task",
    "get_task",
    "list_tasks",
    "add_comment",
    "search_tasks",
    "get_task_history",
    "list_labels",
    "add_label",
    "remove_label",
    "export_project",
    "export_task",
}


class TestMcpToolRegistration:
    """MCP Tool 등록 확인 테스트."""

    async def test_tool_count(self):
        """MCP Tool이 정확히 14개 등록되어 있는지 확인합니다."""
        tools = await mcp.list_tools()
        assert len(tools) == 14, f"예상 14개, 실제 {len(tools)}개: {[t.name for t in tools]}"

    async def test_all_expected_tools_registered(self):
        """모든 예상 Tool 이름이 등록되어 있는지 확인합니다."""
        tools = await mcp.list_tools()
        registered_names = {t.name for t in tools}
        missing = EXPECTED_TOOLS - registered_names
        assert not missing, f"미등록 Tool: {missing}"

    async def test_no_unexpected_tools(self):
        """예상하지 않은 Tool이 등록되지 않았는지 확인합니다."""
        tools = await mcp.list_tools()
        registered_names = {t.name for t in tools}
        extra = registered_names - EXPECTED_TOOLS
        assert not extra, f"예상치 못한 Tool: {extra}"

    async def test_each_tool_has_description(self):
        """각 Tool에 설명(description)이 있는지 확인합니다."""
        tools = await mcp.list_tools()
        for tool in tools:
            assert tool.description, f"Tool '{tool.name}'에 description이 없습니다."
