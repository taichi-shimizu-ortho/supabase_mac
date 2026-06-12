import os
import sys
from datetime import datetime
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
    """医師シフト管理システム - CLI"""
    pass


@cli.command()
def list_doctors():
    """医師一覧を表示"""
    try:
        res = supabase.table("profiles").select("id, full_name, role, is_active").execute()
        if not res.data:
            click.echo("医師がいません")
            return

        click.echo(f"\n👨‍⚕️  医師一覧 ({len(res.data)} 件)")
        click.echo("─" * 70)
        for p in res.data:
            status = "✅" if p["is_active"] else "❌"
            role = "👑 管理者" if p["role"] == "admin" else "医師"
            click.echo(f"{status} {p['full_name']:<20} | {role}")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--doctor", prompt="医師名", help="医師フルネーム")
@click.option("--month", default=None, help="対象月 (YYYY-MM, デフォルト:当月)")
def monthly_count(doctor, month):
    """医師の月別回数を表示"""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    try:
        res = supabase.table("monthly_counts").select(
            "doctor_id, full_name, shift_name, cnt"
        ).eq("full_name", doctor).eq("month", month).execute()

        if not res.data:
            click.echo(f"❌ {doctor} の {month} データがありません")
            return

        click.echo(f"\n📊 {doctor} - {month}")
        click.echo("─" * 40)
        total = 0
        for row in res.data:
            count = row["cnt"]
            total += count
            click.echo(f"  {row['shift_name']:<10}: {count} 回")
        click.echo("─" * 40)
        click.echo(f"  合計       : {total} 回")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


@cli.command()
@click.option("--doctor", prompt="医師名", help="医師フルネーム")
@click.option("--date", prompt="日付", help="日付 (YYYY-MM-DD)")
@click.option("--shift", prompt="シフト種別", type=click.Choice(["当直", "外勤"]), help="シフト種別")
@click.option("--note", default="", help="備考")
def add_assignment(doctor, date, shift, note):
    """シフトを割り当てる（管理者のみ）"""
    try:
        # 医師を検索
        doc_res = supabase.table("profiles").select("id").eq("full_name", doctor).execute()
        if not doc_res.data:
            click.echo(f"❌ 医師 '{doctor}' が見つかりません")
            return
        doctor_id = doc_res.data[0]["id"]

        # シフト種別を検索
        shift_res = supabase.table("shift_types").select("id").eq("name", shift).execute()
        if not shift_res.data:
            click.echo(f"❌ シフト種別 '{shift}' が見つかりません")
            return
        shift_type_id = shift_res.data[0]["id"]

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
@click.option("--month", default=None, help="対象月 (YYYY-MM)")
def summary(month):
    """月別シフト集計を表示"""
    if not month:
        month = datetime.now().strftime("%Y-%m")

    try:
        res = supabase.table("monthly_counts").select(
            "full_name, shift_name, cnt"
        ).eq("month", month).order("full_name").execute()

        if not res.data:
            click.echo(f"❌ {month} のデータがありません")
            return

        click.echo(f"\n📊 {month} 月別集計")
        click.echo("─" * 50)

        current_doctor = None
        for row in res.data:
            if current_doctor != row["full_name"]:
                if current_doctor is not None:
                    click.echo()
                current_doctor = row["full_name"]
                click.echo(f"{current_doctor}:")

            click.echo(f"  {row['shift_name']:<10}: {row['cnt']} 回")
    except Exception as e:
        click.echo(f"❌ エラー: {e}")


if __name__ == "__main__":
    cli()
