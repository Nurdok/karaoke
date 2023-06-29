from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from karaoke.core.base import Base


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    ratings: Mapped[list["UserSongRating"]] = relationship(
        back_populates="user"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.name
