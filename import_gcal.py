#!/usr/bin/env python
"""Google カレンダー取り込み - Google カレンダーを正として勤務表を同期する

Google カレンダーの「iCal 形式の非公開アドレス」(または .ics ファイル) を読み、
指定月の勤務を Google カレンダーの内容に合わせて追加・変更・削除する。

自分 (カレンダーの持ち主) の予定のうち、gcal_places.csv に登録した勤務先を含むものを取り込む。
  「赤池医院」             → 自分が勤務
  「新小倉（藤原先生代理）」→ 自分が藤原医師の代わりに勤務
  「（新小倉）藤原先生」    → 自分の勤務を藤原医師に交代
"""

import csv
import os
import re
import sys
import unicodedata
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from getpass import getpass
from pathlib import Path
from zoneinfo import ZoneInfo

import click
import icalendar
import recurring_ical_events
from dotenv import load_dotenv

load_dotenv()

JST = ZoneInfo("Asia/Tokyo")
DEFAULT_PLACES = "gcal_places.csv"
DEFAULT_ALIASES = "gcal_aliases.csv"
NOTE_TRIM = " \t-–—―・:：/／|｜,，、()（）[]［］【】「」"


@dataclass
class Entry:
    """Google カレンダー上の勤務 1 日分"""
    uid: str
    duty_date: str
    doctor_id: str
    shift_type_id: int
    note: str | None
    summary: str


# ============================================================
# Google カレンダーの読み込み
# ============================================================

def month_range(month: str) -> tuple[date, date]:
    start = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end


def load_calendar(ics_path: str | None) -> icalendar.Calendar:
    if ics_path:
        data = Path(ics_path).read_bytes()
    else:
        # 非公開アドレスを知っていれば誰でも予定を読めるため、.env (Git 管理) には書かない
        url = os.environ.get("GCAL_ICS_URL") or getpass("Google カレンダーの iCal 非公開アドレス: ")
        with urllib.request.urlopen(url, timeout=30) as res:
            data = res.read()
    return icalendar.Calendar.from_ical(data)


def occurrence_dates(event) -> list[date]:
    """勤務日 (日本時間) の一覧。終日予定は各日、時刻付き予定は開始日のみ"""
    start = event["DTSTART"].dt
    if not isinstance(start, datetime):
        end = event["DTEND"].dt if "DTEND" in event else start + timedelta(days=1)
        return [start + timedelta(days=i) for i in range(max((end - start).days, 1))]
    if start.tzinfo is None:
        start = start.replace(tzinfo=JST)
    return [start.astimezone(JST).date()]


# ============================================================
# 予定タイトルの解釈
# ============================================================

def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip()


def name_pattern(name: str) -> re.Pattern:
    # カレンダー側で「清水 太郎」と空白を入れて書かれても一致させる
    chars = [re.escape(c) for c in normalize(name) if not c.isspace()]
    return re.compile(r"\s*".join(chars))


def find_names(text: str, patterns: list[tuple[re.Pattern, object]]) -> list[tuple[int, int, object]]:
    """長い名前を優先し、重ならない一致箇所を返す (「清水太郎」中の「清水」は除く)"""
    hits = [(m.start(), m.end(), value) for pattern, value in patterns for m in pattern.finditer(text)]
    hits.sort(key=lambda h: h[0] - h[1])
    chosen: list[tuple[int, int, object]] = []
    for hit in hits:
        if all(hit[1] <= c[0] or c[1] <= hit[0] for c in chosen):
            chosen.append(hit)
    return chosen


HONORIFIC = re.compile(r"(先生|医師|Dr\.?)")


class SummaryParser:
    """予定タイトルを勤務に変換する

    gcal_places.csv に登録した勤務先を含む予定だけを勤務とみなす。
      「赤池医院」              → 自分が勤務
      「新小倉(藤原先生代理)」  → 自分が勤務 (備考に代理の旨)
      「(新小倉)藤原先生」      → 交代して藤原医師が勤務
    """

    def __init__(self, doctors: list[dict], shift_types: list[dict],
                 places: dict[str, str], aliases: dict[str, str], owner_id: str):
        shift_ids = {normalize(s["name"]): s["id"] for s in shift_types}
        self.place_patterns = []
        for place, shift_name in places.items():
            shift_id = shift_ids.get(normalize(shift_name))
            if shift_id is None:
                raise click.ClickException(f"勤務先 '{place}' のシフト種別 '{shift_name}' が shift_types にありません")
            self.place_patterns.append((name_pattern(place), (place, shift_id)))

        by_name = {normalize(d["full_name"]): d["id"] for d in doctors}
        self.doctor_patterns = [(name_pattern(d["full_name"]), d["id"]) for d in doctors]
        for alias, doctor_name in aliases.items():
            doctor_id = by_name.get(normalize(doctor_name))
            if doctor_id is None:
                raise click.ClickException(f"別名 '{alias}' の医師 '{doctor_name}' が勤務医名簿にありません")
            self.doctor_patterns.append((name_pattern(alias), doctor_id))
        self.doctors = doctors
        self.owner_id = owner_id

    def resolve_doctor(self, text: str) -> str:
        """「藤原先生」などから勤務医を特定する。名簿の名前が「藤原健一」なら名字で前方一致させる"""
        ids = {hit[2] for hit in find_names(text, self.doctor_patterns)}
        if len(ids) == 1:
            return ids.pop()
        if len(ids) > 1:
            raise ValueError("医師名が複数あります")
        name = re.sub(r"\s+", "", HONORIFIC.split(text)[0]).strip(NOTE_TRIM)
        if not name:
            raise ValueError("交代先の医師名がありません")
        candidates = [d for d in self.doctors if re.sub(r"\s+", "", normalize(d["full_name"])).startswith(name)]
        active = [d for d in candidates if d.get("is_active", True)]
        candidates = active or candidates
        if not candidates:
            raise ValueError(f"医師 '{name}' が勤務医名簿にありません (画面の「勤務医を追加」で登録するか gcal_aliases.csv に別名を登録)")
        if len(candidates) > 1:
            names = "、".join(d["full_name"] for d in candidates)
            raise ValueError(f"'{name}' に当たる医師が複数います ({names})。gcal_aliases.csv で指定してください")
        return candidates[0]["id"]

    def parse(self, summary: str) -> tuple[str, int, str | None] | None:
        """(医師ID, シフト種別ID, 備考) を返す。勤務の予定でなければ None、解釈できなければ ValueError"""
        text = normalize(summary)
        places = find_names(text, self.place_patterns)
        if not places:
            if HONORIFIC.search(text) or "代理" in text:
                raise ValueError("勤務先が gcal_places.csv に登録されていません")
            return None
        if len({hit[2] for hit in places}) > 1:
            raise ValueError("勤務先が複数あります")
        start, end, (place, shift_type_id) = places[0]

        before, after = text[:start].strip(), text[end:].strip()
        if before == "(" and after.startswith(")"):
            # 「(勤務先)医師名」: 自分の勤務を他の医師に交代してもらった
            rest = after[1:].strip()
            return self.resolve_doctor(rest), shift_type_id, place
        return self.owner_id, shift_type_id, summary.strip()


def load_mapping(path: str | None, default: str, key: str, value: str) -> dict[str, str]:
    if path is None:
        if not Path(default).exists():
            return {}
        path = default
    with open(path, newline="", encoding="utf-8-sig") as f:
        return {
            row[key].strip(): row[value].strip()
            for row in csv.DictReader(f)
            if (row.get(key) or "").strip()
        }


def collect_entries(cal, months: list[str], parser: SummaryParser):
    """指定月の勤務、解釈できなかった予定 (UIDは保護対象)、勤務以外の予定を返す"""
    ranges = [month_range(m) for m in months]
    first = min(r[0] for r in ranges) - timedelta(days=1)
    last = max(r[1] for r in ranges) + timedelta(days=1)

    entries: list[Entry] = []
    errors: list[str] = []
    protected: set[str] = set()
    skipped: list[str] = []
    seen: dict[tuple, Entry] = {}

    events = recurring_ical_events.of(cal).between(first, last)
    for event in sorted(events, key=lambda e: (str(e["DTSTART"].dt), str(e.get("SUMMARY", "")))):
        if str(event.get("STATUS", "")).upper() == "CANCELLED":
            continue
        dates = [d for d in occurrence_dates(event) if any(s <= d < e for s, e in ranges)]
        if not dates:
            continue
        uid = str(event.get("UID", ""))
        summary = str(event.get("SUMMARY", ""))
        label = f"{dates[0].isoformat()} 「{summary}」"
        if not uid:
            errors.append(f"{label}: UID がありません")
            continue
        try:
            parsed = parser.parse(summary)
        except ValueError as e:
            errors.append(f"{label}: {e}")
            protected.add(uid)
            continue
        if parsed is None:
            skipped.append(label)
            continue

        doctor_id, shift_type_id, note = parsed
        for d in dates:
            entry = Entry(uid, d.isoformat(), doctor_id, shift_type_id, note, summary)
            natural = (doctor_id, shift_type_id, entry.duty_date)
            if natural in seen:
                # 同じ日に同じ医師の外勤が2か所ある場合などは 1 件の勤務にまとめ、備考を並べる
                prev = seen[natural]
                prev.note = " / ".join(n for n in (prev.note, note) if n) or None
                prev.summary = f"{prev.summary} / {summary}"
                continue
            seen[natural] = entry
            entries.append(entry)
    return entries, errors, protected, skipped


# ============================================================
# 差分計算
# ============================================================

def plan_sync(entries: list[Entry], rows: list[dict], protected: set[str]):
    """Google カレンダーに合わせるための (追加, 変更, 削除, 残す手入力) を返す"""
    by_key = {(r["gcal_uid"], r["duty_date"]): r for r in rows if r["gcal_uid"]}
    by_natural = {(r["duty_doctor_id"], r["shift_type_id"], r["duty_date"]): r for r in rows}
    wanted_keys = {(e.uid, e.duty_date) for e in entries}
    used: set[str] = set()
    inserts, updates = [], []

    for e in entries:
        values = {
            "duty_doctor_id": e.doctor_id,
            "shift_type_id": e.shift_type_id,
            "duty_date": e.duty_date,
            "note": e.note,
            "gcal_uid": e.uid,
        }
        row = by_key.get((e.uid, e.duty_date))
        if row is None:
            # 手入力済みの同じ勤務や、作り直された予定の勤務は新規作成せず引き継ぐ
            candidate = by_natural.get((e.doctor_id, e.shift_type_id, e.duty_date))
            if (candidate and candidate["id"] not in used
                    and (candidate["gcal_uid"], candidate["duty_date"]) not in wanted_keys):
                row = candidate
        if row is None:
            inserts.append((e, values))
            continue
        used.add(row["id"])
        changes = {k: v for k, v in values.items() if (row.get(k) or None) != (v or None)}
        if changes:
            updates.append((e, row, changes))

    deletes, manual = [], []
    for r in rows:
        if r["id"] in used or r["gcal_uid"] in protected:
            continue
        # 画面などで手入力した勤務 (他の医師の当直など) はカレンダーになくても残す
        if r["gcal_uid"]:
            deletes.append(r)
        else:
            manual.append(r)
    return inserts, updates, deletes, manual


# ============================================================
# CLI
# ============================================================

@click.command()
@click.option("--month", "months", multiple=True, required=True, help="対象月 (YYYY-MM)。複数指定可")
@click.option("--ics", "ics_path", type=click.Path(exists=True, dir_okay=False), help="URL の代わりに .ics ファイルを読む")
@click.option("--places", "places_path", type=click.Path(exists=True, dir_okay=False),
              help=f"勤務先とシフト種別の対応表 CSV (place,shift_type)。既定: {DEFAULT_PLACES}")
@click.option("--aliases", "aliases_path", type=click.Path(exists=True, dir_okay=False),
              help=f"カレンダー上の表記と勤務医名の対応表 CSV (alias,doctor_name)。既定: {DEFAULT_ALIASES} があれば使用")
@click.option("--owner", envvar="GCAL_OWNER",
              help="カレンダーの持ち主の勤務医名。省略時はサインインした管理者に紐付く勤務医")
@click.option("--show-ignored", is_flag=True, help="勤務先を含まず無視した予定も表示する")
@click.option("--dry-run", is_flag=True, help="変更内容を表示するだけで反映しない")
@click.option("--yes", "-y", is_flag=True, help="確認せずに反映する")
def cli(months, ics_path, places_path, aliases_path, owner, show_ignored, dry_run, yes):
    """指定月の勤務を Google カレンダーの内容に合わせる"""
    for m in months:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", m):
            raise click.BadParameter(f"'{m}' は YYYY-MM 形式ではありません", param_hint="--month")
    months = sorted(set(months))

    click.echo("📍 Google カレンダーを読み込み中...")
    try:
        cal = load_calendar(ics_path)
    except Exception as e:
        raise click.ClickException(f"カレンダーを読み込めませんでした: {e}")
    places = load_mapping(places_path, DEFAULT_PLACES, "place", "shift_type")
    if not places:
        raise click.ClickException(f"勤務先が登録されていません。{DEFAULT_PLACES} に place,shift_type を書いてください")
    aliases = load_mapping(aliases_path, DEFAULT_ALIASES, "alias", "doctor_name")

    from supabase_client import get_client
    supabase = get_client()

    doctors = supabase.table("doctors").select("id, full_name, is_active, profile_id").execute().data
    shift_types = supabase.table("shift_types").select("id, name").execute().data
    if owner:
        matched = [d for d in doctors if normalize(d["full_name"]) == normalize(owner)]
        if not matched:
            raise click.ClickException(f"勤務医 '{owner}' が名簿にありません")
    else:
        session = supabase.auth.get_session()
        user_id = session.user.id if session else None
        matched = [d for d in doctors if user_id and d["profile_id"] == user_id]
        if not matched:
            raise click.ClickException("サインインした利用者に紐付く勤務医がいません。--owner で自分の勤務医名を指定してください")
    owner_id = matched[0]["id"]
    click.echo(f"👤 カレンダーの持ち主: {matched[0]['full_name']}")
    parser = SummaryParser(doctors, shift_types, places, aliases, owner_id)
    entries, errors, protected, skipped = collect_entries(cal, months, parser)

    rows = []
    for m in months:
        start, end = month_range(m)
        rows += supabase.table("assignments").select(
            "id, duty_doctor_id, shift_type_id, duty_date, note, gcal_uid"
        ).gte("duty_date", start.isoformat()).lt("duty_date", end.isoformat()).execute().data
    inserts, updates, deletes, manual = plan_sync(entries, rows, protected)

    doctor_names = {d["id"]: d["full_name"] for d in doctors}
    shift_names = {s["id"]: s["name"] for s in shift_types}

    def describe(doctor_id, shift_type_id, duty_date, note):
        text = f"{duty_date} {doctor_names.get(doctor_id, '不明')} {shift_names.get(shift_type_id, '不明')}"
        return f"{text} ({note})" if note else text

    click.echo(f"\n📅 対象月: {', '.join(months)} / カレンダー上の勤務 {len(entries)} 件\n")
    for e, _ in inserts:
        click.echo(f"  ＋ 追加  {describe(e.doctor_id, e.shift_type_id, e.duty_date, e.note)}")
    for e, row, changes in updates:
        before = describe(row["duty_doctor_id"], row["shift_type_id"], row["duty_date"], row["note"])
        after = describe(e.doctor_id, e.shift_type_id, e.duty_date, e.note)
        detail = f"{before} → {after}" if before != after else f"{before} (Google 予定と紐付け)"
        click.echo(f"  ～ 変更  {detail}")
    for r in deletes:
        click.echo(f"  － 削除  {describe(r['duty_doctor_id'], r['shift_type_id'], r['duty_date'], r['note'])}")
    # 自分の手入力分だけ表示する。他の医師の手入力分はカレンダーと無関係なので件数のみ
    for r in manual:
        if r["duty_doctor_id"] == owner_id:
            click.echo(f"  ？ 手入力のみ (残す)  {describe(r['duty_doctor_id'], r['shift_type_id'], r['duty_date'], r['note'])}")
    if show_ignored:
        for label in skipped:
            click.echo(f"  ・ 勤務先なしで無視  {label}")
    if errors:
        click.echo("\n⚠️  解釈できない予定 (この予定の既存勤務は変更しません):")
        for err in errors:
            click.echo(f"   {err}")

    click.echo(f"\n追加 {len(inserts)} / 変更 {len(updates)} / 削除 {len(deletes)} / エラー {len(errors)}"
               f" / 手入力のみ {len(manual)} (変更しません) / 勤務先なしで無視 {len(skipped)}")
    if skipped and not show_ignored:
        click.echo(f"※ 勤務先が {DEFAULT_PLACES} にない予定は無視しています。一覧は --show-ignored で表示")

    if not (inserts or updates or deletes):
        click.echo("✅ 変更はありません")
        return
    if dry_run:
        click.echo("（--dry-run のため反映していません）")
        return
    if not yes and not click.confirm("反映しますか?"):
        click.echo("中止しました")
        return

    # 削除 → 変更 → 追加の順にして、医師・種別・日付の一意制約に当たりにくくする
    failures = []
    for r in deletes:
        try:
            supabase.table("assignments").delete().eq("id", r["id"]).execute()
        except Exception as e:
            failures.append(f"削除 {r['duty_date']}: {e}")
    for e, row, changes in updates:
        try:
            supabase.table("assignments").update(changes).eq("id", row["id"]).execute()
        except Exception as ex:
            failures.append(f"変更 {e.duty_date} 「{e.summary}」: {ex}")
    for e, values in inserts:
        try:
            supabase.table("assignments").insert(values).execute()
        except Exception as ex:
            failures.append(f"追加 {e.duty_date} 「{e.summary}」: {ex}")

    if failures:
        click.echo("❌ 一部反映できませんでした:")
        for f in failures:
            click.echo(f"   {f}")
        sys.exit(1)
    click.echo("✅ Google カレンダーの内容を反映しました")


if __name__ == "__main__":
    cli()
