from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import Child, Parent
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_parent(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Parent:
    parent_id = decode_access_token(creds.credentials) if creds else None
    parent = db.get(Parent, parent_id) if parent_id else None
    if parent is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parent


CurrentParent = Annotated[Parent, Depends(get_current_parent)]


def owned_child(db: Session, parent: Parent, child_id: str) -> Child:
    """Profil de l'enfant s'il appartient au parent connecté, sinon 404 (existe-t-il ? secret)."""
    child = db.get(Child, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
    return child
