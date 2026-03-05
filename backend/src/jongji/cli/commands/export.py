"""내보내기 CLI 커맨드."""

from __future__ import annotations

import json
import sys

import click

from jongji.cli.client import JongjiClient


@click.group()
def export() -> None:
    """내보내기 관련 커맨드."""


@export.command("project")
@click.argument("project_id")
@click.option("--format", "fmt", default="json", type=click.Choice(["json", "markdown"]), help="내보내기 형식")
@click.pass_context
def export_project(ctx: click.Context, project_id: str, fmt: str) -> None:
    """프로젝트를 내보냅니다.

    PROJECT_ID: 내보낼 프로젝트 ID
    """
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.export_project(project_id=project_id, fmt=fmt)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@export.command("task")
@click.argument("task_id")
@click.option("--format", "fmt", default="json", type=click.Choice(["json", "markdown"]), help="내보내기 형식")
@click.pass_context
def export_task(ctx: click.Context, task_id: str, fmt: str) -> None:
    """업무를 내보냅니다.

    TASK_ID: 내보낼 업무 ID
    """
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.export_task(task_id=task_id, fmt=fmt)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)
