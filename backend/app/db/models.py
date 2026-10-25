from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
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
    lang: Mapped[str] = mapped_column(String(5))
    caution_level: Mapped[str] = mapped_column(String(20), default="standard")
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    needs: Mapped[list[str]] = mapped_column(EncryptedJSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parent: Mapped[Parent] = relationship(back_populates="children")

    @property
    def age(self) -> int:
        return age_on(date.fromisoformat(self.birth_date), date.today())
