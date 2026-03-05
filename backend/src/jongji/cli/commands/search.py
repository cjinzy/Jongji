"""검색 CLI 커맨드."""

from __future__ import annotations

import json
import sys

import click

from jongji.cli.client import JongjiClient


@click.command("search")
@click.option("--query", "-q", required=True, help="검색 쿼리 문자열")
@click.option("--project-id", default=None, help="검색 범위를 제한할 프로젝트 ID")
@click.pass_context
def search(ctx: click.Context, query: str, project_id: str | None) -> None:
    """업무를 검색합니다."""
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.search_tasks(query=query, project_id=project_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)
