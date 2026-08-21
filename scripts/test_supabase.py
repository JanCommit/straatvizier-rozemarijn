import os

from dotenv import load_dotenv
from supabase import create_client


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL ontbreekt in .env")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY ontbreekt in .env")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

response = (
    supabase
    .table("segments")
    .select("id, telraam_segment_id, name, streets(name)")
    .execute()
)

print("Verbinding met Supabase werkt.")
print()
print("Response data:", response.data)

for segment in response.data:
    print(segment)