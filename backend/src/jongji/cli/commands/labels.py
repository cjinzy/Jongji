"""라벨 관련 CLI 커맨드."""

from __future__ import annotations

import json
import sys

import click

from jongji.cli.client import JongjiClient


@click.group()
def labels() -> None:
    """라벨 관련 커맨드."""


@labels.command("list")
@click.option("--project-id", required=True, help="프로젝트 ID")
@click.pass_context
def list_labels(ctx: click.Context, project_id: str) -> None:
    """프로젝트의 라벨 목록을 조회합니다."""
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.list_labels(project_id=project_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@labels.command("add")
@click.option("--task-id", required=True, help="업무 ID")
@click.option("--label-id", required=True, help="라벨 ID")
@click.pass_context
def add_label(ctx: click.Context, task_id: str, label_id: str) -> None:
    """업무에 라벨을 추가합니다."""
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.add_label(task_id=task_id, label_id=label_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)


@labels.command("remove")
@click.option("--task-id", required=True, help="업무 ID")
@click.option("--label-id", required=True, help="라벨 ID")
@click.pass_context
def remove_label(ctx: click.Context, task_id: str, label_id: str) -> None:
    """업무에서 라벨을 제거합니다."""
    client: JongjiClient = ctx.obj["client"]
    try:
        result = client.remove_label(task_id=task_id, label_id=label_id)
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as exc:
        click.echo(f"오류: {exc}", err=True)
        sys.exit(1)
