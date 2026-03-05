"""업무 관련 CLI 커맨드."""

from __future__ import annotations

import json
import sys

import click

from jongji.cli.client import JongjiClient


@click.group()
def tasks() -> None:
    """업무 관련 커맨드."""


@tasks.command("list")
@click.option("--project-id", required=True, help="프로젝트 ID")
@click.option("--status", default=None, help="상태로 필터링")
@click.option("--assignee-id", default=None, help="담당자 ID로 필터링")
@click.pass_context
def list_tasks(ctx: click.Context, project_id: str, status: str | None, assignee_id: str | None) -> None:
    """업무 목록을 조회합니다."""
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.list_tasks(project_id=project_id, status=status, assignee_id=assignee_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@tasks.command("get")
@click.argument("task_id")
@click.pass_context
def get_task(ctx: click.Context, task_id: str) -> None:
    """업무 상세 정보를 조회합니다.

    TASK_ID: 조회할 업무 ID
    """
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.get_task(task_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@tasks.command("create")
@click.option("--project-id", required=True, help="프로젝트 ID")
@click.option("--title", required=True, help="업무 제목")
@click.option("--description", default=None, help="업무 설명")
@click.option("--priority", default=None, help="우선순위 (low/medium/high/urgent)")
@click.option("--assignee-id", default=None, help="담당자 ID")
@click.pass_context
def create_task(
    ctx: click.Context,
    project_id: str,
    title: str,
    description: str | None,
    priority: str | None,
    assignee_id: str | None,
) -> None:
    """새 업무를 생성합니다."""
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.create_task(
            project_id=project_id,
            title=title,
            description=description,
            priority=priority,
            assignee_id=assignee_id,
        )
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@tasks.command("update")
@click.argument("task_id")
@click.option("--title", default=None, help="새 제목")
@click.option("--status", default=None, help="새 상태")
@click.option("--priority", default=None, help="새 우선순위")
@click.option("--assignee-id", default=None, help="새 담당자 ID")
@click.pass_context
def update_task(
    ctx: click.Context,
    task_id: str,
    title: str | None,
    status: str | None,
    priority: str | None,
    assignee_id: str | None,
) -> None:
    """업무를 수정합니다.

    TASK_ID: 수정할 업무 ID
    """
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.update_task(
            task_id=task_id,
            title=title,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
        )
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@tasks.command("comment")
@click.argument("task_id")
@click.option("--content", required=True, help="댓글 내용")
@click.pass_context
def add_comment(ctx: click.Context, task_id: str, content: str) -> None:
    """업무에 댓글을 추가합니다.

    TASK_ID: 댓글을 추가할 업무 ID
    """
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.add_comment(task_id=task_id, content=content)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@tasks.command("history")
@click.argument("task_id")
@click.pass_context
def get_history(ctx: click.Context, task_id: str) -> None:
    """업무 변경 이력을 조회합니다.

    TASK_ID: 이력을 조회할 업무 ID
    """
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.get_task_history(task_id=task_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)
