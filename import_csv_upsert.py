import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase_client import get_client

load_dotenv()

supabase = get_client()

CSV_FILE = "shifts.csv"

if not os.path.exists(CSV_FILE):
    print(f"❌ {CSV_FILE} が見つかりません")
    sys.exit(1)

df = pd.read_csv(CSV_FILE, dtype=str).fillna("")

required_cols = ["doctor_name", "duty_date", "shift_type"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}. Must have: {required_cols}")

df["doctor_name"] = df["doctor_name"].str.strip()
df["duty_date"] = df["duty_date"].str.strip()
df["shift_type"] = df["shift_type"].str.strip()
df["note"] = df.get("note", pd.Series()).fillna("").str.strip()

df = df[(df["doctor_name"] != "") & (df["duty_date"] != "") & (df["shift_type"] != "")]

if len(df) == 0:
    print("❌ 有効なレコードがありません")
    sys.exit(1)

# 医師名から ID を取得
print("📍 医師情報を取得中...")
doctors_res = supabase.table("doctors").select("id, full_name").eq("is_active", True).execute()
doctor_map = {}
for doctor in doctors_res.data:
    doctor_map.setdefault(doctor["full_name"], []).append(doctor["id"])

# シフト種別マスタから ID を取得
print("📍 シフト種別を取得中...")
shift_types_res = supabase.table("shift_types").select("id, name").execute()
shift_type_map = {st["name"]: st["id"] for st in shift_types_res.data}

print(f"✅ 医師 {len(doctor_map)} 件、シフト種別 {len(shift_type_map)} 件")

# CSV を assignments テーブル用に変換
records = []
errors = []

for idx, row in df.iterrows():
    doctor_name = row["doctor_name"]
    shift_name = row["shift_type"]

    if doctor_name not in doctor_map:
        errors.append(f"行{idx+2}: 医師 '{doctor_name}' が見つかりません")
        continue
    if len(doctor_map[doctor_name]) != 1:
        errors.append(f"行{idx+2}: 医師 '{doctor_name}' が複数登録されています")
        continue

    if shift_name not in shift_type_map:
        errors.append(f"行{idx+2}: シフト種別 '{shift_name}' が見つかりません")
        continue

    try:
        # duty_date の形式チェック (YYYY-MM-DD)
        datetime.strptime(row["duty_date"], "%Y-%m-%d")
    except ValueError:
        errors.append(f"行{idx+2}: 日付形式が不正です '{row['duty_date']}'")
        continue

    records.append({
        "duty_doctor_id": doctor_map[doctor_name][0],
        "shift_type_id": shift_type_map[shift_name],
        "duty_date": row["duty_date"],
        "note": row["note"]
    })

if errors:
    print("⚠️  エラー:")
    for err in errors:
        print(f"   {err}")

if records:
    print(f"\n📤 {len(records)} 件をインポート中...")
    try:
        res = supabase.table("assignments").upsert(
            records,
            on_conflict="duty_doctor_id,shift_type_id,duty_date"
        ).execute()
        print(f"✅ {len(res.data)} 件がインポートされました")
    except Exception as e:
        print(f"❌ インポート失敗: {e}")
else:
    print("❌ インポート可能なレコードがありません")
