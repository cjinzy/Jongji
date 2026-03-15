"""전문 검색 서비스.

pg_trgm + tsvector를 결합하여 한국어/영어 혼합 검색을 지원합니다.
"""

import re
import traceback
import uuid

from loguru import logger
from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from jongji.models.enums import TaskStatus
from jongji.models.project import Project
from jongji.models.task import Task, TaskComment, TaskTag
from jongji.schemas.search import SearchResponse, SearchResultItem

# 한글 유니코드 범위 정규식
_KOREAN_RE = re.compile(r"[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]")
# 프로젝트 키+번호 패턴: ABC-123
_PROJ_KEY_RE = re.compile(r"^([A-Z][A-Z0-9]*)-(\d+)$", re.IGNORECASE)


def _is_korean(query: str) -> bool:
    """쿼리에 한글이 포함되어 있는지 확인합니다.

    Args:
        query: 검색어.

    Returns:
        한글 포함 여부.
    """
    return bool(_KOREAN_RE.search(query))


def _parse_tag_query(query: str) -> str | None:
    """태그 검색 쿼리를 파싱합니다 (tag:xxx 또는 #xxx 형식).

    Args:
        query: 검색어.

    Returns:
        태그 문자열 또는 None.
    """
    if query.startswith("tag:"):
        return query[4:].strip()
    if query.startswith("#"):
        return query[1:].strip()
    return None


async def search(
    query: str,
    *,
    project_id: uuid.UUID | None = None,
    tag: str | None = None,
    status: TaskStatus | None = None,
    assignee_id: uuid.UUID | None = None,
    priority: int | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession,
) -> SearchResponse:
    """전문 검색을 수행합니다.

    검색 전략:
    - 태그 쿼리 (tag:xxx 또는 #xxx): task_tags 정확 일치
    - 프로젝트 키+번호 (PROJ-42): tasks.number 정확 일치
    - 한국어 포함: pg_trgm trigram 매칭
    - 영어: tsvector FTS + pg_trgm 병합
    - 댓글: search_vector + trigram 별도 검색 후 UNION

    Args:
        query: 검색어.
        project_id: 프로젝트 필터 UUID.
        tag: 태그 필터 문자열.
        status: 작업 상태 필터.
        assignee_id: 담당자 UUID 필터.
        priority: 우선순위 필터.
        limit: 최대 결과 수.
        offset: 오프셋.
        db: 비동기 DB 세션.

    Returns:
        SearchResponse: 검색 결과.
    """
    try:
        items: list[SearchResultItem] = []

        # 태그 쿼리 파싱 (tag: 또는 # 접두사)
        tag_query = _parse_tag_query(query)
        effective_tag = tag_query or tag

        if tag_query:
            items = await _search_by_tag(
                tag_query,
                project_id=project_id,
                status=status,
                assignee_id=assignee_id,
                priority=priority,
                limit=limit,
                offset=offset,
                db=db,
            )
        else:
            # 프로젝트 키+번호 패턴 감지
            proj_match = _PROJ_KEY_RE.match(query.strip())
            if proj_match:
                items = await _search_by_project_key_number(
                    proj_match.group(1).upper(),
                    int(proj_match.group(2)),
                    project_id=project_id,
                    status=status,
                    assignee_id=assignee_id,
                    priority=priority,
                    limit=limit,
                    offset=offset,
                    db=db,
                )
            else:
                items = await _search_fulltext(
                    query,
                    project_id=project_id,
                    tag=effective_tag,
                    status=status,
                    assignee_id=assignee_id,
                    priority=priority,
                    limit=limit,
                    offset=offset,
                    db=db,
                )

        return SearchResponse(items=items, total=len(items), query=query)

    except Exception:
        logger.error(f"검색 실패: query={query!r}\n{traceback.format_exc()}")
        return SearchResponse(items=[], total=0, query=query)


async def _search_by_tag(
    tag: str,
    *,
    project_id: uuid.UUID | None,
    status: TaskStatus | None,
    assignee_id: uuid.UUID | None,
    priority: int | None,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> list[SearchResultItem]:
    """태그 정확 일치 검색.

    Args:
        tag: 태그 문자열.
        project_id: 프로젝트 필터.
        status: 상태 필터.
        assignee_id: 담당자 필터.
        priority: 우선순위 필터.
        limit: 결과 수.
        offset: 오프셋.
        db: DB 세션.

    Returns:
        검색 결과 목록.
    """
    stmt = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .join(TaskTag, TaskTag.task_id == Task.id)
        .where(TaskTag.tag == tag, Task.is_archived.is_(False))
        .options(contains_eager(Task.project))
    )
    stmt = _apply_task_filters(stmt, project_id, status, assignee_id, priority)
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return [
        SearchResultItem(
            type="task",
            task_id=task.id,
            task_number=task.number,
            task_title=task.title,
            project_key=task.project.key,
            highlight=f"tag:{tag}",
            score=1.0,
        )
        for task in tasks
    ]


async def _search_by_project_key_number(
    key: str,
    number: int,
    *,
    project_id: uuid.UUID | None,
    status: TaskStatus | None,
    assignee_id: uuid.UUID | None,
    priority: int | None,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> list[SearchResultItem]:
    """프로젝트 키+번호 정확 일치 검색 (예: PROJ-42).

    Args:
        key: 프로젝트 키.
        number: 작업 번호.
        project_id: 프로젝트 필터.
        status: 상태 필터.
        assignee_id: 담당자 필터.
        priority: 우선순위 필터.
        limit: 결과 수.
        offset: 오프셋.
        db: DB 세션.

    Returns:
        검색 결과 목록.
    """
    stmt = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(
            Project.key == key,
            Task.number == number,
            Task.is_archived.is_(False),
        )
        .options(contains_eager(Task.project))
    )
    stmt = _apply_task_filters(stmt, project_id, status, assignee_id, priority)
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return [
        SearchResultItem(
            type="task",
            task_id=task.id,
            task_number=task.number,
            task_title=task.title,
            project_key=task.project.key,
            highlight=f"{task.project.key}-{task.number}",
            score=2.0,
        )
        for task in tasks
    ]


async def _search_fulltext(
    query: str,
    *,
    project_id: uuid.UUID | None,
    tag: str | None,
    status: TaskStatus | None,
    assignee_id: uuid.UUID | None,
    priority: int | None,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> list[SearchResultItem]:
    """tsvector + pg_trgm 혼합 전문 검색.

    한국어: trigram 우선, 영어: tsvector + trigram UNION.

    Args:
        query: 검색어.
        project_id: 프로젝트 필터.
        tag: 태그 필터.
        status: 상태 필터.
        assignee_id: 담당자 필터.
        priority: 우선순위 필터.
        limit: 결과 수.
        offset: 오프셋.
        db: DB 세션.

    Returns:
        검색 결과 목록.
    """
    korean = _is_korean(query)
    results: list[SearchResultItem] = []

    # --- 작업 검색 ---
    task_items = await _search_tasks(
        query,
        korean=korean,
        project_id=project_id,
        tag=tag,
        status=status,
        assignee_id=assignee_id,
        priority=priority,
        limit=limit,
        offset=offset,
        db=db,
    )
    results.extend(task_items)

    # --- 댓글 검색 (남은 슬롯만큼) ---
    remaining = limit - len(results)
    if remaining > 0:
        comment_items = await _search_comments(
            query,
            korean=korean,
            project_id=project_id,
            status=status,
            assignee_id=assignee_id,
            priority=priority,
            limit=remaining,
            offset=offset,
            db=db,
        )
        results.extend(comment_items)

    # 점수 내림차순 정렬
    results.sort(key=lambda x: x.score, reverse=True)
    return results


async def _search_tasks(
    query: str,
    *,
    korean: bool,
    project_id: uuid.UUID | None,
    tag: str | None,
    status: TaskStatus | None,
    assignee_id: uuid.UUID | None,
    priority: int | None,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> list[SearchResultItem]:
    """작업 전문 검색 (tsvector + trigram).

    Args:
        query: 검색어.
        korean: 한글 포함 여부.
        project_id: 프로젝트 필터.
        tag: 태그 필터.
        status: 상태 필터.
        assignee_id: 담당자 필터.
        priority: 우선순위 필터.
        limit: 결과 수.
        offset: 오프셋.
        db: DB 세션.

    Returns:
        작업 검색 결과 목록.
    """
    items: list[SearchResultItem] = []

    if korean:
        # 한국어: trigram 유사도 검색
        sim_title = func.similarity(Task.title, query)
        sim_desc = func.similarity(func.coalesce(Task.description, ""), query)
        score_expr = (sim_title + sim_desc * 0.5).label("score")

        stmt = (
            select(Task, score_expr)
            .join(Project, Task.project_id == Project.id)
            .where(
                Task.is_archived.is_(False),
                (sim_title > 0.1) | (sim_desc > 0.1),
            )
            .options(contains_eager(Task.project))
        )
        stmt = _apply_task_filters(stmt, project_id, status, assignee_id, priority)
        if tag:
            stmt = stmt.join(TaskTag, TaskTag.task_id == Task.id).where(TaskTag.tag == tag)
        stmt = stmt.order_by(text("score DESC")).limit(limit).offset(offset)

        result = await db.execute(stmt)
        for task, score in result.all():
            items.append(
                SearchResultItem(
                    type="task",
                    task_id=task.id,
                    task_number=task.number,
                    task_title=task.title,
                    project_key=task.project.key,
                    highlight=task.title[:100],
                    score=float(score),
                )
            )
    else:
        # 영어: tsvector FTS
        ts_query = func.plainto_tsquery("pg_catalog.simple", query)
        ts_rank = func.ts_rank(Task.search_vector, ts_query).label("ts_score")
        sim_title = func.similarity(Task.title, query)

        # tsvector 결과
        ts_stmt = (
            select(Task, ts_rank)
            .join(Project, Task.project_id == Project.id)
            .where(
                Task.is_archived.is_(False),
                Task.search_vector.op("@@")(ts_query),
            )
            .options(contains_eager(Task.project))
        )
        ts_stmt = _apply_task_filters(ts_stmt, project_id, status, assignee_id, priority)
        if tag:
            ts_stmt = ts_stmt.join(TaskTag, TaskTag.task_id == Task.id).where(TaskTag.tag == tag)
        ts_stmt = ts_stmt.order_by(text("ts_score DESC")).limit(limit).offset(offset)

        ts_result = await db.execute(ts_stmt)
        seen_ids: set[uuid.UUID] = set()
        for task, score in ts_result.all():
            seen_ids.add(task.id)
            items.append(
                SearchResultItem(
                    type="task",
                    task_id=task.id,
                    task_number=task.number,
                    task_title=task.title,
                    project_key=task.project.key,
                    highlight=task.title[:100],
                    score=float(score) + 0.5,  # tsvector 결과 우대
                )
            )

        # trigram 보완 (FTS 미매칭 보완)
        remaining = limit - len(items)
        if remaining > 0:
            trgm_stmt = (
                select(Task, sim_title.label("score"))
                .join(Project, Task.project_id == Project.id)
                .where(
                    Task.is_archived.is_(False),
                    Task.id.notin_(list(seen_ids)) if seen_ids else text("TRUE"),
                    sim_title > 0.1,
                )
                .options(contains_eager(Task.project))
            )
            trgm_stmt = _apply_task_filters(trgm_stmt, project_id, status, assignee_id, priority)
            if tag:
                trgm_stmt = trgm_stmt.join(TaskTag, TaskTag.task_id == Task.id).where(
                    TaskTag.tag == tag
                )
            trgm_stmt = trgm_stmt.order_by(text("score DESC")).limit(remaining).offset(offset)

            trgm_result = await db.execute(trgm_stmt)
            for task, score in trgm_result.all():
                items.append(
                    SearchResultItem(
                        type="task",
                        task_id=task.id,
                        task_number=task.number,
                        task_title=task.title,
                        project_key=task.project.key,
                        highlight=task.title[:100],
                        score=float(score),
                    )
                )

    return items


async def _search_comments(
    query: str,
    *,
    korean: bool,
    project_id: uuid.UUID | None,
    status: TaskStatus | None,
    assignee_id: uuid.UUID | None,
    priority: int | None,
    limit: int,
    offset: int,
    db: AsyncSession,
) -> list[SearchResultItem]:
    """댓글 전문 검색.

    Args:
        query: 검색어.
        korean: 한글 포함 여부.
        project_id: 프로젝트 필터.
        status: 상태 필터.
        assignee_id: 담당자 필터.
        priority: 우선순위 필터.
        limit: 결과 수.
        offset: 오프셋.
        db: DB 세션.

    Returns:
        댓글 검색 결과 목록.
    """
    items: list[SearchResultItem] = []

    if korean:
        sim_content = func.similarity(TaskComment.content, query)
        score_expr = sim_content.label("score")

        stmt = (
            select(TaskComment, score_expr)
            .join(Task, TaskComment.task_id == Task.id)
            .join(Project, Task.project_id == Project.id)
            .where(
                Task.is_archived.is_(False),
                sim_content > 0.1,
            )
            .options(
                contains_eager(TaskComment.task).contains_eager(Task.project)
            )
        )
        stmt = _apply_task_filters(stmt, project_id, status, assignee_id, priority, task_model=Task)
        stmt = stmt.order_by(text("score DESC")).limit(limit).offset(offset)

        result = await db.execute(stmt)
        for comment, score in result.all():
            task = comment.task
            items.append(
                SearchResultItem(
                    type="comment",
                    task_id=task.id,
                    task_number=task.number,
                    task_title=task.title,
                    project_key=task.project.key,
                    highlight=comment.content[:100],
                    score=float(score) * 0.8,  # 댓글은 작업보다 낮은 가중치
                )
            )
    else:
        ts_query = func.plainto_tsquery("pg_catalog.simple", query)
        ts_rank = func.ts_rank(TaskComment.search_vector, ts_query).label("score")

        stmt = (
            select(TaskComment, ts_rank)
            .join(Task, TaskComment.task_id == Task.id)
            .join(Project, Task.project_id == Project.id)
            .where(
                Task.is_archived.is_(False),
                TaskComment.search_vector.op("@@")(ts_query),
            )
            .options(
                contains_eager(TaskComment.task).contains_eager(Task.project)
            )
        )
        stmt = _apply_task_filters(stmt, project_id, status, assignee_id, priority, task_model=Task)
        stmt = stmt.order_by(text("score DESC")).limit(limit).offset(offset)

        result = await db.execute(stmt)
        for comment, score in result.all():
            task = comment.task
            items.append(
                SearchResultItem(
                    type="comment",
                    task_id=task.id,
                    task_number=task.number,
                    task_title=task.title,
                    project_key=task.project.key,
                    highlight=comment.content[:100],
                    score=float(score) * 0.8,
                )
            )

    return items


def _apply_task_filters(
    stmt: Select,
    project_id: uuid.UUID | None,
    status: TaskStatus | None,
    assignee_id: uuid.UUID | None,
    priority: int | None,
    *,
    task_model: type[Task] | None = None,
) -> Select:
    """공통 작업 필터를 적용합니다.

    Args:
        stmt: SQLAlchemy select 구문.
        project_id: 프로젝트 UUID 필터.
        status: 상태 필터.
        assignee_id: 담당자 UUID 필터.
        priority: 우선순위 필터.
        task_model: Task 모델 클래스 (기본값: Task).

    Returns:
        필터가 적용된 select 구문.
    """
    t = task_model or Task
    if project_id is not None:
        stmt = stmt.where(t.project_id == project_id)
    if status is not None:
        stmt = stmt.where(t.status == status)
    if assignee_id is not None:
        stmt = stmt.where(t.assignee_id == assignee_id)
    if priority is not None:
        stmt = stmt.where(t.priority == priority)
    return stmt
