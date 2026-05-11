import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"Connecting to: {url}")
try:
    supabase = create_client(url, key)
    # Try to list tables by fetching one row
    res = supabase.from_("breathing_records").select("*").limit(1).execute()
    print("✅ Success! Data:", res.data)
except Exception as e:
    print("❌ Error:", e)