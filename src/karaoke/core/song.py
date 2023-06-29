from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String


from karaoke.core.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from karaoke.core.rating import UserSongRating


class Song(Base):
    __tablename__ = "song"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    artist: Mapped[str] = mapped_column(String(100))
    video_link: Mapped[str] = mapped_column(String(500))
    ratings: Mapped[list["UserSongRating"]] = relationship(
        back_populates="song"
    )

    def __repr__(self) -> str:
        return (
            f"Song(id={self.id}, "
            f"title={self.title}, "
            f"artist={self.artist}, "
            f"video_link={self.video_link})"
        )
