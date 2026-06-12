import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase = create_client(url, key)

print("✅ Connected to:", url)

# テーブルの存在確認
try:
    res = supabase.table("profiles").select("*", count="exact").limit(1).execute()
    print(f"✅ profiles テーブル OK - {res.count} 件")
except Exception as e:
    print(f"❌ profiles テーブル ERROR: {e}")

try:
    res = supabase.table("assignments").select("*", count="exact").limit(1).execute()
    print(f"✅ assignments テーブル OK - {res.count} 件")
except Exception as e:
    print(f"❌ assignments テーブル ERROR: {e}")

try:
    res = supabase.table("shift_types").select("*").execute()
    print(f"✅ shift_types テーブル OK - {len(res.data)} 件")
    for st in res.data:
        print(f"   - {st['id']}: {st['name']} ({st['color']})")
except Exception as e:
    print(f"❌ shift_types テーブル ERROR: {e}")
