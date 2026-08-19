import re
from datetime import date, timedelta

def normalize_phone(raw: str) -> str:
    """Приводит любой формат к +371XXXXXXXX."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00371"):
        digits = digits[2:]
    if digits.startswith("371"):
        digits = "+" + digits
    elif digits.startswith("2") and len(digits) == 8:
        digits = "+371" + digits
    if not digits.startswith("+371"):
        raise ValueError("Телефон должен быть латвийским (+371)")
    if not re.match(r"^\+371\d{7,11}$", digits):
        raise ValueError("Неверный формат номера")
    return digits

def days_to_payment(next_payment_date: date) -> int:
    return (next_payment_date - date.today()).days

def payment_date_from_days(days: int) -> date:
    return date.today() + timedelta(days=days)