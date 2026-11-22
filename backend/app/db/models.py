from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.age import age_on
from app.db.types import EncryptedJSON, EncryptedText


def _new_id() -> str:
    return uuid4().hex


class Base(DeclarativeBase):
    pass


class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    pin_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    children: Mapped[list["Child"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", order_by="Child.created_at"
    )


class Child(Base):
    __tablename__ = "children"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    parent_id: Mapped[str] = mapped_column(ForeignKey("parents.id", ondelete="CASCADE"), index=True)
    first_name: Mapped[str] = mapped_column(String(50))
    avatar: Mapped[str] = mapped_column(String(16))
    # Données sensibles chiffrées en base (NF-06) : date de naissance et besoins d'adaptation.
    birth_date: Mapped[str] = mapped_column(EncryptedText)
    sex: Mapped[str] = mapped_column(String(20))
    grade: Mapped[str] = mapped_column(String(20))
    caution_level: Mapped[str] = mapped_column(String(20), default="standard")
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    needs: Mapped[list[str]] = mapped_column(EncryptedJSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parent: Mapped[Parent] = relationship(back_populates="children")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="child", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def age(self) -> int:
        return age_on(date.fromisoformat(self.birth_date), date.today())


class Message(Base):
    """Une question de l'enfant et la réponse affichée (section 15).

    latency_ms : temps total (contrôles + génération) ; safety_latency_ms : part des contrôles.
    model_name / prompt_version sont vides quand Kotty n'a pas été appelé (question bloquée).
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(16))
    lang: Mapped[str] = mapped_column(String(5))
    input_risk: Mapped[str] = mapped_column(String(16))
    input_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_check: Mapped[str] = mapped_column(String(16))
    rag_ref: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer)
    safety_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Politique qui a choisi l'action (b2-rules-v1, puis versions RL) : comparaison à l'étape 10.
    policy_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    child: Mapped[Child] = relationship(back_populates="messages")


class Alert(Base):
    """Alerte au parent quand Kotty choisit ASK_ADULT (F-P03, section 15)."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(16), default="ASK_ADULT")
    seen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    message: Mapped[Message] = relationship()
