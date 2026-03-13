"""Jongji CLI 엔트리포인트."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

import click

from jongji.cli.client import JongjiClient
from jongji.cli.commands.export import export
from jongji.cli.commands.labels import labels
from jongji.cli.commands.projects import projects
from jongji.cli.commands.search import search
from jongji.cli.commands.tasks import tasks


def _load_config() -> dict[str, Any]:
    """~/.jongji/config.toml 설정 파일을 로드합니다.

    Returns:
        설정 딕셔너리 (파일이 없으면 빈 딕셔너리 반환)
    """
    config_path = Path.home() / ".jongji" / "config.toml"
    if config_path.exists():
        try:
            with config_path.open("rb") as f:
                return tomllib.load(f)
        except Exception as exc:  # noqa: BLE001
            click.echo(f"경고: 설정 파일 로드 실패 ({config_path}): {exc}", err=True)
    return {}


@click.group()
@click.option("--api-key", envvar="JONGJI_API_KEY", default=None, help="API 인증 키 (환경변수: JONGJI_API_KEY)")
@click.option(
    "--server-url",
    envvar="JONGJI_SERVER_URL",
    default=None,
    help="서버 URL (환경변수: JONGJI_SERVER_URL, 기본: http://localhost:8888)",
)
@click.pass_context
def app(ctx: click.Context, api_key: str | None, server_url: str | None) -> None:
    """Jongji CLI - 프로젝트 관리 도구."""
    ctx.ensure_object(dict)

    config = _load_config()

    resolved_api_key = api_key or config.get("api_key")
    resolved_server_url = server_url or config.get("server_url", "http://localhost:8888")

    if not resolved_api_key:
        click.echo(
            "경고: API 키가 설정되지 않았습니다. "
            "JONGJI_API_KEY 환경변수 또는 ~/.jongji/config.toml의 api_key를 설정하세요.",
            err=True,
        )

    ctx.obj["client"] = JongjiClient(server_url=resolved_server_url, api_key=resolved_api_key)


app.add_command(projects)
app.add_command(tasks)
app.add_command(search)
app.add_command(labels)
app.add_command(export)


def main() -> None:
    """CLI 메인 진입점."""
    try:
        app()
    except SystemExit:
        raise
    except Exception as exc:
        click.echo(f"예기치 않은 오류: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
