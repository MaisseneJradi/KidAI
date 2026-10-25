from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentParent, DbSession
from app.core.security import create_access_token, hash_secret, verify_secret
from app.db.models import Parent
from app.schemas import LoginIn, PinIn, RegisterIn, TokenOut

router = APIRouter(prefix="/api/auth/parent", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: DbSession) -> TokenOut:
    email = payload.email.lower()
    if db.scalar(select(Parent).where(Parent.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet email")
    parent = Parent(
        email=email,
        password_hash=hash_secret(payload.password),
        pin_hash=hash_secret(payload.pin),
    )
    db.add(parent)
    db.commit()
    return TokenOut(access_token=create_access_token(parent.id))


@router.post("/login")
def login(payload: LoginIn, db: DbSession) -> TokenOut:
    parent = db.scalar(select(Parent).where(Parent.email == payload.email.lower()))
    if parent is None or not verify_secret(parent.password_hash, payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou mot de passe incorrect")
    return TokenOut(access_token=create_access_token(parent.id))


@router.post("/pin")
def check_pin(payload: PinIn, parent: CurrentParent) -> dict[str, bool]:
    # 403 (et non 401) : la session reste valide, seul le PIN est faux.
    if not verify_secret(parent.pin_hash, payload.pin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "PIN incorrect")
    return {"ok": True}
