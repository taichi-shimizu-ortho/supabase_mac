#!/usr/bin/env python
"""シフト管理 - 割り当ての追加・削除・確認"""

import os
from datetime import datetime, timedelta
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
    """シフト管理ツール"""
    pass


@cli.command()
@click.option("--month", default=None, help="対象月 (YYYY-MM)")
def list_assignments(month):
    """月別シフト一覧を表示"""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    try:
        # 来月の初日を計算
        month_dt = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        next_month = month_dt + timedelta(days=32)
        next_month_str = next_month.strftime("%Y-%m-01")

        # duty_date が該当月のものを取得
        res = supabase.table("assignments").select(
            "id, doctor_id, shift_type_id, duty_date, note, " +
            "profiles!assignments_doctor_id_fkey(full_name), shift_types(name)"
        ).gte("duty_date", f"{month}-01").lt("duty_date", next_month_str).order(
            "duty_date"
        ).execute()

        if not res.data:
            click.echo(f"❌ {month} のシフト割り当てがありません")
            return

        click.echo(f"\n📅 {month} のシフト割り当て ({len(res.data)} 件)")
        click.echo("─" * 80)
        click.echo(f"{'Date':<12} | {'Doctor':<20} | {'Shift':<10} | {'Note':<30}")
        click.echo("─" * 80)

        for a in res.data:
            doctor_name = a["profiles"]["full_name"]
            shift_name = a["shift_types"]["name"]
            note = a.get("note", "")
            click.echo(
                f"{a['duty_date']:<12} | {doctor_name:<20} | {shift_name:<10} | {note:<30}"
            )
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--doctor", prompt="医師名", help="医師フルネーム")
@click.option("--date", prompt="日付", help="日付 (YYYY-MM-DD)")
@click.option("--shift", prompt="シフト種別", type=click.Choice(["当直", "外勤"]), help="シフト種別")
@click.option("--note", default="", help="備考")
def add(doctor, date, shift, note):
    """シフトを割り当てる"""
    try:
        # 医師を検索
        doc_res = supabase.table("profiles").select("id").eq("full_name", doctor).eq(
            "is_active", True
        ).execute()
        if not doc_res.data:
            click.echo(f"❌ 医師 '{doctor}' が見つかりません（非アクティブの可能性）")
            return
        doctor_id = doc_res.data[0]["id"]

        # シフト種別を検索
        shift_res = supabase.table("shift_types").select("id").eq("name", shift).execute()
        if not shift_res.data:
            click.echo(f"❌ シフト種別 '{shift}' が見つかりません")
            return
        shift_type_id = shift_res.data[0]["id"]

        # 日付の検証
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            click.echo("❌ 日付形式が不正です (YYYY-MM-DD の形式で入力してください)")
            return

        # インサート
        res = supabase.table("assignments").insert({
            "doctor_id": doctor_id,
            "shift_type_id": shift_type_id,
            "duty_date": date,
            "note": note
        }).execute()

        click.echo(f"✅ {doctor} に {date} の {shift} を割り当てました")
    except Exception as e:
        if "unique" in str(e).lower():
            click.echo(f"⚠️  既に同じ割り当てが存在します")
        else:
            click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--id", prompt="Assignment ID", help="削除対象の割り当てID")
@click.confirmation_option(prompt="本当に削除しますか?")
def delete(id):
    """割り当てを削除"""
    try:
        res = supabase.table("assignments").delete().eq("id", id).execute()

        if res.data:
            click.echo(f"✅ 割り当てを削除しました")
        else:
            click.echo(f"❌ ID {id} が見つかりません")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--doctor", prompt="医師名", help="医師フルネーム")
@click.option("--month", default=None, help="対象月 (YYYY-MM)")
def doctor_shifts(doctor, month):
    """特定医師の月別シフトを表示"""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    try:
        # 医師を検索
        doc_res = supabase.table("profiles").select("id").eq("full_name", doctor).execute()
        if not doc_res.data:
            click.echo(f"❌ 医師 '{doctor}' が見つかりません")
            return
        doctor_id = doc_res.data[0]["id"]

        # 来月の初日を計算
        month_dt = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        next_month = month_dt + timedelta(days=32)
        next_month_str = next_month.strftime("%Y-%m-01")

        # シフトを検索
        res = supabase.table("assignments").select(
            "id, duty_date, note, shift_types(name)"
        ).eq("doctor_id", doctor_id).gte("duty_date", f"{month}-01").lt(
            "duty_date", next_month_str
        ).order("duty_date").execute()

        click.echo(f"\n📅 {doctor} - {month} のシフト ({len(res.data)} 件)")
        click.echo("─" * 60)

        if not res.data:
            click.echo("  (該当なし)")
            return

        for a in res.data:
            shift_name = a["shift_types"]["name"]
            note = a.get("note", "")
            click.echo(f"  {a['duty_date']} {shift_name:<10} | {note}")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


if __name__ == "__main__":
    cli()
