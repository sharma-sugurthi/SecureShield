import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("backend/.env")

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

res = supabase.auth.sign_in_with_password({"email": "test@example.com", "password": "password"})
print("Algorithm:", __import__("jwt").get_unverified_header(res.session.access_token))
