from datetime import date
from typing import Literal

MIN_AGE = 6
MAX_AGE = 14

# Tranches d'âge du cahier des charges (mêmes bornes que frontend/src/lib/ageBand.ts).
AgeBand = Literal["small", "middle", "teen"]


def age_on(birth_date: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


def age_band(age: int) -> AgeBand:
    """6–8 ans : « small », 9–11 ans : « middle », 12–14 ans : « teen »."""
    if age <= 8:
        return "small"
    if age <= 11:
        return "middle"
    return "teen"
