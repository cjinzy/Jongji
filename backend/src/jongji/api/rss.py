"""RSS 피드 API 엔드포인트.

프로젝트의 task_history를 RSS 2.0 형식으로 제공합니다.
인증 없이 공개적으로 접근 가능합니다.
"""

import uuid
import xml.etree.ElementTree as ET
from email.utils import format_datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.database import get_db
from jongji.models.project import Project
from jongji.models.task import Task, TaskHistory
from jongji.models.user import User

router = APIRouter(prefix="/api/v1", tags=["rss"])


def _build_rss_xml(project: Project, items: list[dict]) -> str:
    """RSS 2.0 XML 문자열을 생성합니다.

    Args:
        project: 프로젝트 모델 인스턴스.
        items: RSS 아이템 딕셔너리 목록 (title, link, description, pubDate).

    Returns:
        RSS 2.0 XML 문자열.
    """
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = f"Jongji - {project.name}"
    ET.SubElement(channel, "link").text = f"/projects/{project.id}"
    ET.SubElement(channel, "description").text = project.description or f"{project.name} 작업 피드"
    ET.SubElement(channel, "language").text = "ko"

    for item in items:
        item_el = ET.SubElement(channel, "item")
        ET.SubElement(item_el, "title").text = item.get("title", "")
        ET.SubElement(item_el, "link").text = item.get("link", "")
        ET.SubElement(item_el, "description").text = item.get("description", "")
        ET.SubElement(item_el, "pubDate").text = item.get("pubDate", "")
        ET.SubElement(item_el, "guid").text = item.get("guid", item.get("link", ""))

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode")


@router.get(
    "/projects/{project_id}/rss",
    summary="프로젝트 RSS 피드",
    description="프로젝트의 작업 변경 이력을 RSS 2.0 형식으로 반환합니다. 인증 불필요.",
    response_class=Response,
)
async def get_project_rss(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """프로젝트의 task_history를 RSS 2.0 피드로 반환합니다.

    Args:
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.

    Returns:
        RSS XML 응답 (Content-Type: application/rss+xml).

    Raises:
        HTTPException: 프로젝트가 존재하지 않으면 404.
    """
    # 프로젝트 조회
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    # task_history 조회 (최근 50건)
    history_result = await db.execute(
        select(TaskHistory, Task, User)
        .join(Task, TaskHistory.task_id == Task.id)
        .join(User, TaskHistory.user_id == User.id)
        .where(Task.project_id == project_id)
        .order_by(TaskHistory.created_at.desc())
        .limit(50)
    )
    rows = history_result.all()

    items: list[dict] = []
    for history, task, user in rows:
        title = f"[{task.title}] {history.field} 변경"
        description = (
            f"{user.name}이(가) '{history.field}'을(를) "
            f"'{history.old_value}' → '{history.new_value}'(으)로 변경했습니다."
        )
        pub_date = format_datetime(history.created_at)
        link = f"/projects/{project_id}/tasks/{task.id}"
        guid = str(history.id)

        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "pubDate": pub_date,
                "guid": guid,
            }
        )

    xml_content = _build_rss_xml(project, items)
    return Response(
        content=xml_content,
        media_type="application/rss+xml",
    )
