import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_KEY")
)

# リレーションなしで直接取得
print("=== リレーションなし ===")
res = supabase.table("assignments").select("*").execute()
print(f"件数: {len(res.data)}")
if res.data:
    print(f"最初のレコード: {res.data[0]}")

# 医師情報
print("\n=== 医師情報 ===")
res = supabase.table("profiles").select("*").execute()
print(f"医師数: {len(res.data)}")
for p in res.data:
    print(f"  {p['full_name']} - {p['id']}")

# シフト種別
print("\n=== シフト種別 ===")
res = supabase.table("shift_types").select("*").execute()
print(f"シフト種別: {len(res.data)}")
for s in res.data:
    print(f"  {s['id']}: {s['name']}")
