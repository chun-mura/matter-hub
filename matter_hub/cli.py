"""CLI entry point for Matter Hub."""

import os
import sys
import time

import click
import qrcode
from rich.console import Console
from rich.table import Table

from matter_hub.api import MatterClient, parse_feed_entry
from matter_hub.config import load_config, save_config, get_db_path
from matter_hub.db import Database

console = Console()


def get_client_from_config() -> MatterClient:
    config = load_config()
    access_token = config.get("access_token")
    refresh_token = config.get("refresh_token")
    if not access_token:
        console.print("[red]未認証です。先に `matter-hub auth` を実行してください。[/red]")
        sys.exit(1)
    return MatterClient(access_token=access_token, refresh_token=refresh_token)


def get_db() -> Database:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return Database(db_path)


@click.group()
def cli():
    """Matter Hub - Matter記事の検索・タグ管理CLI"""
    pass


@cli.command()
def auth():
    """QRコード認証でMatterにログイン"""
    client = MatterClient()
    session_token = client.trigger_qr_login()

    console.print("\n[bold]MatterアプリでこのQRコードをスキャンしてください:[/bold]")
    console.print("[dim]Profile > Settings > Connected Accounts > Obsidian > Scan QR Code[/dim]\n")

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(session_token)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    console.print("\n[yellow]スキャン待機中...[/yellow]")

    for _ in range(600):
        result = client.exchange_token(session_token)
        if result:
            save_config({
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
            })
            console.print("[green]認証成功！トークンを保存しました。[/green]")
            return
        time.sleep(1)

    console.print("[red]タイムアウト: 10分以内にスキャンされませんでした。[/red]")
    sys.exit(1)
