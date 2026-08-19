from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional
from .auth import get_current_user
from .db import get_supabase
from .utils import normalize_phone

router = APIRouter(prefix="/api/cards", tags=["cards"])


class CardIn(BaseModel):
    phone_number: str
    balance: float = Field(ge=0, decimal_places=2)
    next_payment_date: date
    note: Optional[str] = ""

    @field_validator("phone_number")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        try:
            return normalize_phone(v)
        except ValueError as e:
            raise ValueError(str(e))


class CardOut(CardIn):
    id: int
    created_at: date


@router.get("/", response_model=list[CardOut])
async def list_cards(user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = (
        sb.table("cards")
        .select("*")
        .eq("user_id", user["id"])
        .order("next_payment_date", desc=False)
        .execute()
    )
    return res.data or []


@router.post("/", response_model=CardOut, status_code=status.HTTP_201_CREATED)
async def create_card(card: CardIn, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    # Проверка уникальности
    existing = (
        sb.table("cards")
        .select("id")
        .eq("user_id", user["id"])
        .eq("phone_number", card.phone_number)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Номер уже добавлен")

    payload = {**card.model_dump(), "user_id": user["id"]}
    res = sb.table("cards").insert(payload).execute()
    return res.data[0]


@router.put("/{card_id}", response_model=CardOut)
async def update_card(card_id: int, card: CardIn, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    # Убедимся, что карта принадлежит юзеру
    current = sb.table("cards").select("*").eq("id", card_id).eq("user_id", user["id"]).execute()
    if not current.data:
        raise HTTPException(status_code=404, detail="Карта не найдена")

    payload = card.model_dump()
    res = sb.table("cards").update(payload).eq("id", card_id).execute()
    return res.data[0]


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: int, user: dict = Depends(get_current_user)):
    sb = get_supabase()
    res = sb.table("cards").delete().eq("id", card_id).eq("user_id", user["id"]).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Карта не найдена")