import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

payload = {
    "staff_name": "Shimizu",
    "shift_date": "2026-06-11",
    "shift_type": "night",
    "note": "test"
}

res = supabase.table("on_call_shifts").insert(payload).execute()
print(res.data)
