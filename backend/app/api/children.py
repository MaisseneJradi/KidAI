from fastapi import APIRouter, Response, status

from app.api.deps import CurrentParent, DbSession, owned_child
from app.db.models import Child
from app.schemas import ChildIn, ChildOut, ChildPatch

router = APIRouter(prefix="/api/children", tags=["children"])


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
    child = owned_child(db, parent, child_id)
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(child, field, value.isoformat() if field == "birth_date" else value)
    db.commit()
    return ChildOut.model_validate(child)


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_child(child_id: str, parent: CurrentParent, db: DbSession) -> Response:
    db.delete(owned_child(db, parent, child_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
