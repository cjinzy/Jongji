"""Dashboard 응답 Pydantic 스키마.

프로젝트 대시보드 집계 데이터를 직렬화합니다.
"""

from uuid import UUID

from pydantic import BaseModel


class StatusCountItem(BaseModel):
    """상태별 업무 수 아이템.

    Attributes:
        status: 작업 상태 문자열.
        count: 해당 상태의 작업 수.
    """

    status: str
    count: int


class PriorityDistributionItem(BaseModel):
    """우선순위별 업무 수 아이템.

    Attributes:
        priority: 우선순위 값 (1-9).
        count: 해당 우선순위의 작업 수.
    """

    priority: int
    count: int


class AssigneeWorkloadItem(BaseModel):
    """담당자별 미완료 업무 수 아이템.

    Attributes:
        user_id: 담당자 UUID.
        user_name: 담당자 이름.
        count: 미완료 작업 수.
    """

    user_id: UUID
    user_name: str
    count: int


class DailyCountItem(BaseModel):
    """일별 업무 수 아이템.

    Attributes:
        date: 날짜 문자열 (YYYY-MM-DD).
        count: 해당 날짜의 작업 수.
    """

    date: str
    count: int


class LabelDistributionItem(BaseModel):
    """라벨별 업무 수 아이템.

    Attributes:
        label_id: 라벨 UUID.
        label_name: 라벨 이름.
        color: 라벨 색상.
        count: 해당 라벨이 달린 작업 수.
    """

    label_id: UUID
    label_name: str
    color: str
    count: int


class DashboardResponse(BaseModel):
    """프로젝트 대시보드 집계 응답 스키마.

    Attributes:
        status_counts: 상태별 업무 수 딕셔너리.
        priority_distribution: 우선순위별 업무 수 목록.
        assignee_workload: 담당자별 미완료 업무 수 목록.
        daily_created: 최근 30일 일별 생성 업무 수.
        daily_completed: 최근 30일 일별 완료 업무 수.
        label_distribution: 라벨별 업무 수 목록.
        total_tasks: 전체 업무 수.
        completed_tasks: 완료된 업무 수.
        completion_rate: 완료율 (0.0~1.0).
    """

    status_counts: dict[str, int]
    priority_distribution: list[PriorityDistributionItem]
    assignee_workload: list[AssigneeWorkloadItem]
    daily_created: list[DailyCountItem]
    daily_completed: list[DailyCountItem]
    label_distribution: list[LabelDistributionItem]
    total_tasks: int
    completed_tasks: int
    completion_rate: float
