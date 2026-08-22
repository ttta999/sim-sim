import os
import re
import json
import hmac
import hashlib
import logging
from datetime import date, timedelta, datetime, timezone
from functools import lru_cache
from typing import Optional
from urllib.parse import parse_qs

from fastapi import FastAPI, Depends, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from mangum import Mangum
from pydantic import BaseModel, Field, field_validator
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sim-sim")

# ================= Supabase =================
@lru_cache()
def get_supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# ================= Telegram auth =================
tg_header = APIKeyHeader(name="X-Telegram-Init-Data", auto_error=False)

def verify_init_data(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")
    parsed = parse_qs(init_data, keep_blank_values=True)
    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash")

    data_check_string = "\n".join(f"{k}={parsed[k][0]}" for k in sorted(parsed.keys()))
    secret_key = hmac.new(b"WebAppData", os.environ["TELEGRAM_BOT_TOKEN"].encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(status_code=401, detail="Invalid signature")

    auth_date = int(parsed.get("auth_date", ["0"])[0])
    if datetime.now(timezone.utc).timestamp() - auth_date > 86400:
        raise HTTPException(status_code=401, detail="Init data expired")

    user_str = parsed.get("user", [None])[0]
    if not user_str:
        raise HTTPException(status_code=401, detail="No user in initData")
    return json.loads(user_str)

async def get_current_user(init_data: Optional[str] = Security(tg_header)) -> dict:
    return verify_init_data(init_data or "")

# ================= Helpers =================
def _check(p: str) -> str:
    if not re.match(r"^\+371\d{7,11}$", p):
        raise ValueError("Invalid phone format")
    return p

def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00371"):
        digits = digits[2:]
    if digits.startswith("371"):
        return _check("+" + digits)
    if digits.startswith("2") and len(digits) == 8:
        return _check("+371" + digits)
    raise ValueError("Phone must be Latvian (+371)")

def plural_days(n: int) -> str:
    n = abs(n) % 100
    if 10 < n < 20:
        return "дней"
    last = n % 10
    if last == 1:
        return "день"
    if 2 <= last <= 4:
        return "дня"
    return "дней"

# ================= Schema =================
class CardIn(BaseModel):
    phone_number: str
    balance: float = Field(ge=0)
    next_payment_date: date
    note: Optional[str] = ""

    @field_validator("phone_number")
    @classmethod
    def _norm(cls, v: str) -> str:
        try:
            return normalize_phone(v)
        except ValueError as e:
            raise ValueError(str(e))

# ================= App =================
app = FastAPI(title="SIM Card Tracker API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/debug")
async def debug():
    result = {"env": {}}
    for var in ("TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY", "CRON_SECRET"):
        val = os.environ.get(var)
        result["env"][var] = {"present": bool(val), "length": len(val) if val else 0}
    try:
        sb = get_supabase()
        sb.table("cards").select("id").limit(1).execute()
        result["supabase"] = {"ok": True}
    except Exception as e:
        result["supabase"] = {"ok": False, "error": str(e)[:300]}
    return result

@app.get("/api/cards")
async def list_cards(user: dict = Depends(get_current_user)):
    res = (get_supabase().table("cards").select("*")
           .eq("user_id", user["id"])
           .order("next_payment_date", desc=False).execute())
    return res.data or []

@app.post("/api/cards", status_code=status.HTTP_201_CREATED)
async def create_card(card: CardIn, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    existing = (sb.table("cards").select("id")
                .eq("user_id", user["id"])
                .eq("phone_number", card.phone_number).execute())
    if existing.data:
        raise HTTPException(status_code=409, detail="Этот номер уже добавлен")
    payload = {**card.model_dump(), "user_id": user["id"]}
    res = sb.table("cards").insert(payload).execute()
    return res.data[0]

@app.put("/api/cards/{card_id}")
async def update_card(card_id: int, card: CardIn, user: dict = Depends(get_current_user)):
    res = (get_supabase().table("cards").update(card.model_dump())
           .eq("id", card_id).eq("user_id", user["id"]).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Карта не найдена")
    return res.data[0]

@app.delete("/api/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: int, user: dict = Depends(get_current_user)):
    res = (get_supabase().table("cards").delete()
           .eq("id", card_id).eq("user_id", user["id"]).execute())
    if not res.data:
        raise HTTPException(status_code=404, detail="Карта не найдена")

# ================= Cron notifications =================
# ВАЖНО: Vercel Cron всегда отправляет GET-запрос (не POST!), и не использует
# заголовок "x-vercel-cron" (такого не существует). Защита идёт через
# CRON_SECRET, который Vercel автоматически подставляет как
# "Authorization: Bearer <CRON_SECRET>", если эта переменная задана
# в Project Settings -> Environment Variables.
@app.get("/api/cron_notify")
async def cron_notify(request: Request):
    if os.environ.get("VERCEL") == "1":
        auth = request.headers.get("authorization")
        expected = f"Bearer {os.environ.get('CRON_SECRET')}"
        if not os.environ.get("CRON_SECRET") or auth != expected:
            raise HTTPException(status_code=403, detail="Forbidden")

    from aiogram import Bot
    from aiogram.exceptions import TelegramForbiddenError

    sb = get_supabase()
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    today = date.today()
    sent = 0
    try:
        for offset in (3, 1, 0):
            target = today + timedelta(days=offset)
            res = sb.table("cards").select("*").eq("next_payment_date", target.isoformat()).execute()
            for card in res.data or []:
                word = plural_days(offset)
                head = {0: "🔴 СРОЧНО! Срок аванса истекает сегодня!",
                        1: "⚠️ Требуется пополнение!",
                        3: f"⚠️ Осталось {offset} {word} до оплаты"}[offset]
                msg = (f"{head}\n\n📱 Номер: {card['phone_number']}\n"
                       f"💰 Баланс: {float(card['balance']):.2f} €\n"
                       f"⏳ Осталось: {offset} {word} (до {target.strftime('%d.%m.%Y')})\n")
                if card.get("note"):
                    msg += f"📝 Заметка: {card['note']}"
                try:
                    await bot.send_message(chat_id=card["user_id"], text=msg)
                    sent += 1
                except TelegramForbiddenError:
                    log.warning("User %s не запустил бота", card["user_id"])
                except Exception as e:
                    log.error("Send failed: %s", e)
    finally:
        await bot.session.close()
    return {"ok": True, "sent": sent}

# Vercel entry point
handler = Mangum(app, lifespan="off")