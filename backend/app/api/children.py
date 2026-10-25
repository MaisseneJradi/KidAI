from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentParent, DbSession
from app.db.models import Child, Parent
from app.schemas import ChildIn, ChildOut, ChildPatch

router = APIRouter(prefix="/api/children", tags=["children"])


def _owned_child(db: DbSession, parent: Parent, child_id: str) -> Child:
    child = db.get(Child, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
    return child


@router.get("")
def list_children(parent: CurrentParent) -> list[ChildOut]:
    return [ChildOut.model_validate(c) for c in parent.children]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_child(payload: ChildIn, parent: CurrentParent, db: DbSession) -> ChildOut:
    data = payload.model_dump()
    data["birth_date"] = payload.birth_date.isoformat()
    child = Child(parent_id=parent.id, **data)
    db.add(child)
    db.commit()
    return ChildOut.model_validate(child)


@router.patch("/{child_id}")
def update_child(
    child_id: str, payload: ChildPatch, parent: CurrentParent, db: DbSession
) -> ChildOut:
    child = _owned_child(db, parent, child_id)
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(child, field, value.isoformat() if field == "birth_date" else value)
    db.commit()
    return ChildOut.model_validate(child)


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_child(child_id: str, parent: CurrentParent, db: DbSession) -> Response:
    db.delete(_owned_child(db, parent, child_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
