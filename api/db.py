import os
from supabase import create_client, Client
from functools import lru_cache

@lru_cache()
def get_supabase() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],
    )