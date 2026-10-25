from datetime import date
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
)

from app.core.age import MAX_AGE, MIN_AGE, age_on

Sex = Literal["fille", "garcon", "non_precise"]
Lang = Literal["fr", "ar"]
CautionLevel = Literal["standard", "renforce"]
Interest = Literal["sciences", "espace", "animaux", "histoire", "corps", "sport", "musique", "art"]
# Besoins d'adaptation : seulement ce que l'interface et Chaty savent prendre en compte.
Need = Literal["dyslexie", "deficience_visuelle", "attention", "deficience_auditive"]

FirstName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
Grade = Annotated[str, StringConstraints(pattern=r"^[1-9]e_annee$")]
Pin = Annotated[str, StringConstraints(pattern=r"^\d{4}$")]


def _check_age(birth_date: date) -> date:
    if not MIN_AGE <= age_on(birth_date, date.today()) <= MAX_AGE:
        raise ValueError(f"L'enfant doit avoir entre {MIN_AGE} et {MAX_AGE} ans")
    return birth_date


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


BirthDate = Annotated[date, AfterValidator(_check_age)]
Interests = Annotated[list[Interest], Field(max_length=8), AfterValidator(_unique)]
Needs = Annotated[list[Need], Field(max_length=4), AfterValidator(_unique)]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    pin: Pin


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class PinIn(BaseModel):
    pin: Pin


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class ChildIn(BaseModel):
    first_name: FirstName
    avatar: str = Field(min_length=1, max_length=16)
    birth_date: BirthDate
    sex: Sex
    grade: Grade
    lang: Lang
    caution_level: CautionLevel = "standard"
    interests: Interests = []
    needs: Needs = []


class ChildPatch(BaseModel):
    first_name: FirstName | None = None
    avatar: str | None = Field(default=None, min_length=1, max_length=16)
    birth_date: BirthDate | None = None
    sex: Sex | None = None
    grade: Grade | None = None
    lang: Lang | None = None
    caution_level: CautionLevel | None = None
    interests: Interests | None = None
    needs: Needs | None = None


class ChildOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    first_name: str
    avatar: str
    birth_date: date
    age: int
    sex: Sex
    grade: str
    lang: Lang
    caution_level: CautionLevel
    interests: list[Interest]
    needs: list[Need]
