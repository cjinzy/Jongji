"""Jongji REST API HTTP 클라이언트."""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger


class JongjiClient:
    """Jongji 백엔드 REST API와 통신하는 동기 HTTP 클라이언트."""

    def __init__(self, server_url: str, api_key: str | None = None) -> None:
        """클라이언트를 초기화합니다.

        Args:
            server_url: Jongji 서버 URL (예: http://localhost:8888)
            api_key: 인증에 사용할 API 키 (없으면 인증 없이 요청)
        """
        self.server_url = server_url.rstrip("/")
        headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(base_url=self.server_url, headers=headers, timeout=30.0)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """HTTP 요청을 수행하고 JSON 응답을 반환합니다.

        Args:
            method: HTTP 메서드 (GET, POST, PATCH, DELETE)
            path: API 경로 (예: /api/v1/projects)
            **kwargs: httpx.Client.request에 전달할 추가 인자

        Returns:
            파싱된 JSON 응답

        Raises:
            SystemExit: HTTP 오류 발생 시 exit code 1로 종료
        """
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            if response.content:
                return response.json()
            return None
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP 오류: {} {} - {}",
                exc.response.status_code,
                exc.request.url,
                exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("요청 실패: {} - {}", exc.request.url, exc)
            raise

    # ─── Projects ────────────────────────────────────────────────────────────

    def list_projects(self, team_id: str | None = None) -> Any:
        """프로젝트 목록을 반환합니다.

        Args:
            team_id: 필터링할 팀 ID (선택)

        Returns:
            프로젝트 목록 JSON
        """
        params: dict[str, str] = {}
        if team_id:
            params["team_id"] = team_id
        return self._request("GET", "/api/v1/projects", params=params)

    def get_project(self, project_id: str) -> Any:
        """단일 프로젝트를 반환합니다.

        Args:
            project_id: 프로젝트 ID

        Returns:
            프로젝트 JSON
        """
        return self._request("GET", f"/api/v1/projects/{project_id}")

    # ─── Tasks ───────────────────────────────────────────────────────────────

    def list_tasks(
        self,
        project_id: str,
        status: str | None = None,
        assignee_id: str | None = None,
    ) -> Any:
        """프로젝트의 업무 목록을 반환합니다.

        Args:
            project_id: 프로젝트 ID
            status: 필터링할 상태 (선택)
            assignee_id: 필터링할 담당자 ID (선택)

        Returns:
            업무 목록 JSON
        """
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        if assignee_id:
            params["assignee_id"] = assignee_id
        return self._request("GET", f"/api/v1/projects/{project_id}/tasks", params=params)

    def get_task(self, task_id: str) -> Any:
        """단일 업무를 반환합니다.

        Args:
            task_id: 업무 ID

        Returns:
            업무 JSON
        """
        return self._request("GET", f"/api/v1/tasks/{task_id}")

    def create_task(
        self,
        project_id: str,
        title: str,
        description: str | None = None,
        priority: str | None = None,
        assignee_id: str | None = None,
    ) -> Any:
        """새 업무를 생성합니다.

        Args:
            project_id: 프로젝트 ID
            title: 업무 제목
            description: 업무 설명 (선택)
            priority: 우선순위 (선택)
            assignee_id: 담당자 ID (선택)

        Returns:
            생성된 업무 JSON
        """
        body: dict[str, Any] = {"title": title}
        if description is not None:
            body["description"] = description
        if priority is not None:
            body["priority"] = priority
        if assignee_id is not None:
            body["assignee_id"] = assignee_id
        return self._request("POST", f"/api/v1/projects/{project_id}/tasks", json=body)

    def update_task(
        self,
        task_id: str,
        title: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee_id: str | None = None,
    ) -> Any:
        """업무를 수정합니다.

        Args:
            task_id: 업무 ID
            title: 새 제목 (선택)
            status: 새 상태 (선택)
            priority: 새 우선순위 (선택)
            assignee_id: 새 담당자 ID (선택)

        Returns:
            수정된 업무 JSON
        """
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if status is not None:
            body["status"] = status
        if priority is not None:
            body["priority"] = priority
        if assignee_id is not None:
            body["assignee_id"] = assignee_id
        return self._request("PATCH", f"/api/v1/tasks/{task_id}", json=body)

    def add_comment(self, task_id: str, content: str) -> Any:
        """업무에 댓글을 추가합니다.

        Args:
            task_id: 업무 ID
            content: 댓글 내용

        Returns:
            생성된 댓글 JSON
        """
        return self._request("POST", f"/api/v1/tasks/{task_id}/comments", json={"content": content})

    def get_task_history(self, task_id: str) -> Any:
        """업무 변경 이력을 반환합니다.

        Args:
            task_id: 업무 ID

        Returns:
            업무 이력 JSON
        """
        return self._request("GET", f"/api/v1/tasks/{task_id}/history")

    # ─── Search ──────────────────────────────────────────────────────────────

    def search_tasks(self, query: str, project_id: str | None = None) -> Any:
        """업무를 검색합니다.

        Args:
            query: 검색 쿼리 문자열
            project_id: 검색 범위를 제한할 프로젝트 ID (선택)

        Returns:
            검색 결과 JSON
        """
        params: dict[str, str] = {"q": query}
        if project_id:
            params["project_id"] = project_id
        return self._request("GET", "/api/v1/search", params=params)

    # ─── Labels ──────────────────────────────────────────────────────────────

    def list_labels(self, project_id: str) -> Any:
        """프로젝트의 라벨 목록을 반환합니다.

        Args:
            project_id: 프로젝트 ID

        Returns:
            라벨 목록 JSON
        """
        return self._request("GET", f"/api/v1/projects/{project_id}/labels")

    def add_label(self, task_id: str, label_id: str) -> Any:
        """업무에 라벨을 추가합니다.

        Args:
            task_id: 업무 ID
            label_id: 라벨 ID

        Returns:
            업데이트된 업무 JSON
        """
        return self._request("POST", f"/api/v1/tasks/{task_id}/labels", json={"label_id": label_id})

    def remove_label(self, task_id: str, label_id: str) -> Any:
        """업무에서 라벨을 제거합니다.

        Args:
            task_id: 업무 ID
            label_id: 라벨 ID

        Returns:
            업데이트된 업무 JSON 또는 None
        """
        return self._request("DELETE", f"/api/v1/tasks/{task_id}/labels/{label_id}")

    # ─── Export ──────────────────────────────────────────────────────────────

    def export_project(self, project_id: str, fmt: str = "json") -> Any:
        """프로젝트를 내보냅니다.

        Args:
            project_id: 프로젝트 ID
            fmt: 내보내기 형식 (json 또는 markdown)

        Returns:
            내보내기 데이터 JSON
        """
        return self._request("GET", f"/api/v1/projects/{project_id}/export", params={"format": fmt})

    def export_task(self, task_id: str, fmt: str = "json") -> Any:
        """업무를 내보냅니다.

        Args:
            task_id: 업무 ID
            fmt: 내보내기 형식 (json 또는 markdown)

        Returns:
            내보내기 데이터 JSON
        """
        return self._request("GET", f"/api/v1/tasks/{task_id}/export", params={"format": fmt})

    def close(self) -> None:
        """HTTP 클라이언트를 닫습니다."""
        self._client.close()

    def __enter__(self) -> JongjiClient:
        """컨텍스트 매니저 진입."""
        return self

    def __exit__(self, *args: Any) -> None:
        """컨텍스트 매니저 종료 시 클라이언트를 닫습니다."""
        self.close()
