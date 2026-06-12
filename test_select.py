import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

res = supabase.table("on_call_shifts").select("*").limit(5).execute()
print(res.data)
