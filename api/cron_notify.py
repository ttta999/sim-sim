import os
from datetime import date, timedelta
from fastapi import APIRouter, Request, HTTPException
from aiogram.exceptions import TelegramForbiddenError
from .db import get_supabase
from .bot import get_bot

router = APIRouter()

def plural_days(n: int) -> str:
    n = abs(n) % 100
    n1 = n % 10
    if 10 < n < 20:
        return "дней"
    if n1 == 1:
        return "день"
    if 2 <= n1 <= 4:
        return "дня"
    return "дней"


@router.post("/api/cron_notify")
async def cron_notify(request: Request):
    # Защита: Vercel добавляет этот заголовок
    if request.headers.get("x-vercel-cron") is None and os.environ.get("VERCEL") == "1":
        raise HTTPException(status_code=403, detail="Forbidden")

    sb = get_supabase()
    bot = get_bot()
    today = date.today()

    sent = 0
    for offset in (3, 1, 0):
        target = today + timedelta(days=offset)
        res = sb.table("cards").select("*").eq("next_payment_date", target.isoformat()).execute()
        for card in res.data or []:
            days = offset
            days_word = plural_days(days)
            if days == 0:
                days_word = "дней"
                emoji_line = "🔴 СРОЧНО! Срок аванса истёк сегодня!"
            elif days == 1:
                emoji_line = "⚠️ Требуется пополнение!"
            else:
                emoji_line = f"⚠️ Осталось {days} {days_word} до оплаты"

            msg = (
                f"{emoji_line}\n\n"
                f"📱 Номер: {card['phone_number']}\n"
                f"💰 Баланс: {float(card['balance']):.2f} €\n"
                f"⏳ Осталось: {days} {days_word} (до {target.strftime('%d.%m.%Y')})\n"
            )
            if card.get("note"):
                msg += f"📝 Заметка: {card['note']}"

            try:
                await bot.send_message(chat_id=card["user_id"], text=msg)
                sent += 1
            except TelegramForbiddenError:
                # Юзер не подписался на бота — пропускаем
                continue
            except Exception as e:
                print(f"Failed to send to {card['user_id']}: {e}")

    await bot.session.close()
    return {"ok": True, "sent": sent}