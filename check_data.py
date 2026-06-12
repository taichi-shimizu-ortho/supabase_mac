import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

# すべてのデータを確認
res = supabase.table("assignments").select("*").execute()
print(f"全割り当て: {len(res.data)} 件")
for a in res.data:
    print(f"  日付: {a['duty_date']}, 医師ID: {a['doctor_id']}, シフト種別ID: {a['shift_type_id']}")

# 2026-08 のデータ
res = supabase.table("assignments").select("*").gte("duty_date", "2026-08-01").lt("duty_date", "2026-09-01").execute()
print(f"\n2026-08 のデータ: {len(res.data)} 件")
for a in res.data:
    print(f"  {a['duty_date']} - 医師ID: {a['doctor_id']}, シフト種別ID: {a['shift_type_id']}")
