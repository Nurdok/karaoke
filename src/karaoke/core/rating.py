from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

from karaoke.core.base import Base
from karaoke.core.song import Song
from karaoke.core.user import User


class Rating(Enum):
    DONT_KNOW = 0
    SING_ALONG = 1
    CAN_TAKE_THE_MIC = 2
    NEED_THE_MIC = 3


class UserSongRating(Base):
    __tablename__ = "user_song_rating"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id"), primary_key=True
    )
    user: Mapped[User] = relationship(back_populates="ratings")
    song_id: Mapped[int] = mapped_column(
        ForeignKey("song.id"), primary_key=True
    )
    song: Mapped[Song] = relationship(back_populates="ratings")
    rating: Mapped[Rating] = mapped_column()

    def __repr__(self) -> str:
        return f"UserSongRating(user_id={self.user_id}, song_id={self.song_id}, rating={self.rating})"
