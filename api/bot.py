import os
from aiogram import Bot
from functools import lru_cache

@lru_cache()
def get_bot() -> Bot:
    return Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])