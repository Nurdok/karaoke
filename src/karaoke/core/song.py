from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String


from karaoke.core.base import Base


class Song(Base):
    __tablename__ = "song"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    artist: Mapped[str] = mapped_column(String(100))
    video_link: Mapped[str] = mapped_column(String(500))

    def __repr__(self):
        return f"Song(id={self.id}, title={self.title}, artist={self.artist}, video_link={self.video_link})"
