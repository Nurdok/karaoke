from sqlalchemy import ForeignKey, String, Integer, Column, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

from karaoke.core.base import Base


session_user_association_table = Table(
    "session_user_association",
    Base.metadata,
    Column("session", String(4), ForeignKey("session.session_id")),
    Column("user", Integer, ForeignKey("user_account.id")),
)


class SessionUser(Base):
    __tablename__ = "session_user"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("session.session_id"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id"), primary_key=True
    )
    score: Mapped[int] = mapped_column()


class SessionSong(Base):
    __tablename__ = "session_song"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("session.session_id"), primary_key=True
    )
    song_id: Mapped[int] = mapped_column(
        ForeignKey("song.id"), primary_key=True
    )
    played: Mapped[bool] = mapped_column()


class Session(Base):
    __tablename__ = "session"

    session_id: Mapped[str] = mapped_column(String(4), primary_key=True)
    users: Mapped[list[SessionUser]] = relationship()
    songs: Mapped[list[SessionSong]] = relationship()
