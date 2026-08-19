import os
import hmac
import hashlib
from urllib.parse import parse_qs, unquote
from datetime import datetime, timezone
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

tg_header = APIKeyHeader(name="X-Telegram-Init-Data", auto_error=False)

def verify_telegram_init_data(init_data: str) -> dict:
    """Проверяет подпись initData через HMAC-SHA256 и возвращает user."""
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")

    parsed = parse_qs(init_data, keep_blank_values=True)
    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash")

    # data_check_string = sorted key=value pairs, joined by \n
    data_pairs = []
    for key in sorted(parsed.keys()):
        val = parsed[key][0]
        data_pairs.append(f"{key}={val}")
    data_check_string = "\n".join(data_pairs)

    # secret = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData",
        os.environ["TELEGRAM_BOT_TOKEN"].encode(),
        hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Проверяем, что данные не устарели (опционально, 24 часа)
    auth_date = int(parsed.get("auth_date", [0])[0])
    if datetime.now(timezone.utc).timestamp() - auth_date > 86400:
        raise HTTPException(status_code=401, detail="Init data expired")

    # Извлекаем user (JSON-строка в поле user)
    import json
    user_str = parsed.get("user", [None])[0]
    if not user_str:
        raise HTTPException(status_code=401, detail="No user in initData")
    return json.loads(user_str)


async def get_current_user(init_data: str = Security(tg_header)) -> dict:
    return verify_telegram_init_data(init_data)