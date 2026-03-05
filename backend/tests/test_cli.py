"""CLI 커맨드 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from jongji.cli.main import app

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def runner() -> CliRunner:
    """Click 테스트 러너를 반환합니다."""
    return CliRunner()


@pytest.fixture()
def mock_client() -> MagicMock:
    """JongjiClient 목 객체를 반환합니다."""
    client = MagicMock()
    return client


def _invoke_with_mock(runner: CliRunner, mock_client: MagicMock, args: list[str]) -> Any:
    """목 클라이언트를 주입하면서 CLI를 호출하는 헬퍼.

    Args:
        runner: CliRunner 인스턴스
        mock_client: 주입할 MagicMock 클라이언트
        args: CLI 인자 목록

    Returns:
        CliRunner 호출 결과
    """
    with patch("jongji.cli.main.JongjiClient", return_value=mock_client):
        return runner.invoke(app, ["--api-key", "test-key"] + args, catch_exceptions=False)


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestProjectsList:
    """projects list 커맨드 테스트."""

    def test_projects_list_success(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """projects list가 JSON을 출력하고 exit code 0을 반환하는지 검증합니다."""
        mock_client.list_projects.return_value = [{"id": "p1", "name": "프로젝트 A"}]

        result = _invoke_with_mock(runner, mock_client, ["projects", "list"])

        assert result.exit_code == 0
        assert '"id": "p1"' in result.output
        assert '"name": "프로젝트 A"' in result.output
        mock_client.list_projects.assert_called_once_with(team_id=None)

    def test_projects_list_with_team_id(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """--team-id 옵션이 클라이언트에 전달되는지 검증합니다."""
        mock_client.list_projects.return_value = []

        result = _invoke_with_mock(runner, mock_client, ["projects", "list", "--team-id", "team-123"])

        assert result.exit_code == 0
        mock_client.list_projects.assert_called_once_with(team_id="team-123")

    def test_projects_list_error(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """API 오류 시 exit code 1을 반환하는지 검증합니다."""
        mock_client.list_projects.side_effect = Exception("서버 오류")

        with patch("jongji.cli.main.JongjiClient", return_value=mock_client):
            result = runner.invoke(app, ["--api-key", "test-key", "projects", "list"])

        assert result.exit_code == 1


class TestTasksCreate:
    """tasks create 커맨드 테스트."""

    def test_tasks_create_success(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """tasks create가 올바른 인자를 전달하고 JSON을 출력하는지 검증합니다."""
        mock_client.create_task.return_value = {
            "id": "t1",
            "title": "새 업무",
            "project_id": "p1",
        }

        result = _invoke_with_mock(
            runner,
            mock_client,
            ["tasks", "create", "--project-id", "p1", "--title", "새 업무"],
        )

        assert result.exit_code == 0
        assert '"id": "t1"' in result.output
        mock_client.create_task.assert_called_once_with(
            project_id="p1",
            title="새 업무",
            description=None,
            priority=None,
            assignee_id=None,
        )

    def test_tasks_create_with_all_options(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """모든 옵션을 지정했을 때 올바르게 전달되는지 검증합니다."""
        mock_client.create_task.return_value = {"id": "t2", "title": "상세 업무"}

        result = _invoke_with_mock(
            runner,
            mock_client,
            [
                "tasks",
                "create",
                "--project-id",
                "p1",
                "--title",
                "상세 업무",
                "--description",
                "설명",
                "--priority",
                "high",
                "--assignee-id",
                "user-1",
            ],
        )

        assert result.exit_code == 0
        mock_client.create_task.assert_called_once_with(
            project_id="p1",
            title="상세 업무",
            description="설명",
            priority="high",
            assignee_id="user-1",
        )


class TestTasksGet:
    """tasks get 커맨드 테스트."""

    def test_tasks_get_success(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """tasks get이 JSON을 출력하고 exit code 0을 반환하는지 검증합니다."""
        mock_client.get_task.return_value = {"id": "task-abc", "title": "조회 업무"}

        result = _invoke_with_mock(runner, mock_client, ["tasks", "get", "task-abc"])

        assert result.exit_code == 0
        assert '"id": "task-abc"' in result.output
        mock_client.get_task.assert_called_once_with("task-abc")

    def test_tasks_get_not_found(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """업무가 없을 때 exit code 1을 반환하는지 검증합니다."""
        mock_client.get_task.side_effect = Exception("404 Not Found")

        with patch("jongji.cli.main.JongjiClient", return_value=mock_client):
            result = runner.invoke(app, ["--api-key", "test-key", "tasks", "get", "not-exist"])

        assert result.exit_code == 1


class TestSearch:
    """search 커맨드 테스트."""

    def test_search_success(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """search가 쿼리를 전달하고 JSON을 출력하는지 검증합니다."""
        mock_client.search_tasks.return_value = {"results": [{"id": "t1", "title": "검색 결과"}]}

        result = _invoke_with_mock(runner, mock_client, ["search", "--query", "검색어"])

        assert result.exit_code == 0
        assert "검색 결과" in result.output
        mock_client.search_tasks.assert_called_once_with(query="검색어", project_id=None)

    def test_search_with_project_id(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """--project-id 옵션이 클라이언트에 전달되는지 검증합니다."""
        mock_client.search_tasks.return_value = {"results": []}

        result = _invoke_with_mock(
            runner, mock_client, ["search", "--query", "키워드", "--project-id", "p-999"]
        )

        assert result.exit_code == 0
        mock_client.search_tasks.assert_called_once_with(query="키워드", project_id="p-999")


class TestExport:
    """export 커맨드 테스트."""

    def test_export_project_success(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """export project가 JSON을 출력하고 exit code 0을 반환하는지 검증합니다."""
        mock_client.export_project.return_value = {"project": "data"}

        result = _invoke_with_mock(runner, mock_client, ["export", "project", "proj-1"])

        assert result.exit_code == 0
        assert '"project": "data"' in result.output
        mock_client.export_project.assert_called_once_with(project_id="proj-1", fmt="json")

    def test_export_task_success(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """export task가 JSON을 출력하고 exit code 0을 반환하는지 검증합니다."""
        mock_client.export_task.return_value = {"task": "data"}

        result = _invoke_with_mock(runner, mock_client, ["export", "task", "task-1"])

        assert result.exit_code == 0
        assert '"task": "data"' in result.output
        mock_client.export_task.assert_called_once_with(task_id="task-1", fmt="json")

    def test_export_project_markdown_format(self, runner: CliRunner, mock_client: MagicMock) -> None:
        """--format=markdown 옵션이 클라이언트에 전달되는지 검증합니다."""
        mock_client.export_project.return_value = {"markdown": "# 프로젝트"}

        result = _invoke_with_mock(
            runner, mock_client, ["export", "project", "proj-2", "--format", "markdown"]
        )

        assert result.exit_code == 0
        mock_client.export_project.assert_called_once_with(project_id="proj-2", fmt="markdown")
