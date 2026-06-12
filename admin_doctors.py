#!/usr/bin/env python
"""医師管理 - 医師の追加・削除・ロール管理"""

import os
from dotenv import load_dotenv
from supabase import create_client
import click

load_dotenv()

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)


@click.group()
def cli():
    """医師管理ツール"""
    pass


@cli.command()
def list_all():
    """全医師一覧を表示"""
    try:
        res = supabase.table("profiles").select(
            "id, full_name, role, is_active, created_at"
        ).order("created_at", desc=False).execute()

        if not res.data:
            click.echo("医師がいません")
            return

        click.echo(f"\n👨‍⚕️  全医師一覧 ({len(res.data)} 件)")
        click.echo("─" * 80)
        click.echo(f"{'Name':<20} | {'Role':<10} | {'Status':<10} | {'Created':<20}")
        click.echo("─" * 80)

        for p in res.data:
            status = "✅ Active" if p["is_active"] else "❌ Inactive"
            role = "👑 Admin" if p["role"] == "admin" else "医師"
            created = p["created_at"][:10] if p["created_at"] else "N/A"
            click.echo(f"{p['full_name']:<20} | {role:<10} | {status:<10} | {created:<20}")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--id", prompt="User ID (UUID)", help="Supabase Auth の User ID")
@click.option("--name", prompt="Full Name", help="医師フルネーム")
def add(id, name):
    """既存のAuth ユーザーを医師として追加"""
    try:
        res = supabase.table("profiles").insert({
            "id": id,
            "full_name": name,
            "role": "doctor",
            "is_active": True
        }).execute()

        click.echo(f"✅ {name} を医師として登録しました")
        click.echo(f"   ID: {id}")
    except Exception as e:
        if "duplicate" in str(e).lower():
            click.echo(f"⚠️  既に登録されています")
        else:
            click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--name", prompt="医師名", help="削除対象の医師フルネーム")
@click.confirmation_option(prompt="本当に削除しますか?")
def delete(name):
    """医師を削除"""
    try:
        res = supabase.table("profiles").delete().eq("full_name", name).execute()

        if res.data:
            click.echo(f"✅ {name} を削除しました")
        else:
            click.echo(f"❌ {name} が見つかりません")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--name", prompt="医師名", help="対象医師")
def set_admin(name):
    """医師を管理者に昇格"""
    try:
        res = supabase.table("profiles").update({"role": "admin"}).eq(
            "full_name", name
        ).execute()

        if res.data:
            click.echo(f"✅ {name} を管理者に昇格しました")
        else:
            click.echo(f"❌ {name} が見つかりません")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--name", prompt="医師名", help="対象医師")
def set_doctor(name):
    """管理者を通常医師に降格"""
    try:
        res = supabase.table("profiles").update({"role": "doctor"}).eq(
            "full_name", name
        ).execute()

        if res.data:
            click.echo(f"✅ {name} を通常医師に降格しました")
        else:
            click.echo(f"❌ {name} が見つかりません")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--name", prompt="医師名", help="対象医師")
def disable(name):
    """医師を無効化（表示されなくなる）"""
    try:
        res = supabase.table("profiles").update({"is_active": False}).eq(
            "full_name", name
        ).execute()

        if res.data:
            click.echo(f"✅ {name} を無効化しました")
        else:
            click.echo(f"❌ {name} が見つかりません")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--name", prompt="医師名", help="対象医師")
def enable(name):
    """医師を有効化"""
    try:
        res = supabase.table("profiles").update({"is_active": True}).eq(
            "full_name", name
        ).execute()

        if res.data:
            click.echo(f"✅ {name} を有効化しました")
        else:
            click.echo(f"❌ {name} が見つかりません")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


if __name__ == "__main__":
    cli()
