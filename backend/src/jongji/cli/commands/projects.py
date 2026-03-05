"""프로젝트 관련 CLI 커맨드."""

from __future__ import annotations

import json
import sys

import click

from jongji.cli.client import JongjiClient


@click.group()
def projects() -> None:
    """프로젝트 관련 커맨드."""


@projects.command("list")
@click.option("--team-id", default=None, help="팀 ID로 필터링")
@click.pass_context
def list_projects(ctx: click.Context, team_id: str | None) -> None:
    """프로젝트 목록을 조회합니다."""
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.list_projects(team_id=team_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@projects.command("get")
@click.argument("project_id")
@click.pass_context
def get_project(ctx: click.Context, project_id: str) -> None:
    """프로젝트 상세 정보를 조회합니다.

    PROJECT_ID: 조회할 프로젝트 ID
    """
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.get_project(project_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)
