from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentParent, DbSession
from app.db.models import Alert, Child
from app.schemas import AlertOut

router = APIRouter(prefix="/api/parent", tags=["parent"])


@router.get("/alerts")
def list_alerts(parent: CurrentParent, db: DbSession) -> list[AlertOut]:
    """Alertes ASK_ADULT de tous les enfants du parent connecté, les plus récentes d'abord."""
    alerts = db.scalars(
        select(Alert)
        .join(Child, Alert.child_id == Child.id)
        .where(Child.parent_id == parent.id)
        .options(selectinload(Alert.message))
        .order_by(Alert.created_at.desc())
    ).all()
    return [
        AlertOut(
            id=a.id,
            child_id=a.child_id,
            message_id=a.message_id,
            type="ASK_ADULT",
            question=a.message.question,
            seen=a.seen,
            created_at=a.created_at,
        )
        for a in alerts
    ]
