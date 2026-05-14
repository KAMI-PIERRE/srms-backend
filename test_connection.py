from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    result = supabase.from_("users").select("*", count="exact").execute()
    print("Connection successful. Users count:", result.count)
except Exception as e:
    print("Error:", str(e))