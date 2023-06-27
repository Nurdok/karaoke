from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from enum import Enum
import random
import logging

from karaoke.core.base import Base
from karaoke.core.rating import UserSongRating
from karaoke.core.song import Song

logger = logging.getLogger(__name__)


class KaraokeSessionUser(Base):
    __tablename__ = "karaoke_session_user"

    karaoke_session_id: Mapped[str] = mapped_column(
        ForeignKey("karaoke_session.id"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id"), primary_key=True
    )
    score: Mapped[int] = mapped_column(default=0)


class KaraokeSessionSong(Base):
    __tablename__ = "karaoke_session_song"

    karaoke_session_id: Mapped[str] = mapped_column(
        ForeignKey("karaoke_session.id"), primary_key=True
    )
    song_id: Mapped[int] = mapped_column(
        ForeignKey("song.id"), primary_key=True
    )
    played: Mapped[bool] = mapped_column()


def generate_id() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choices(letters, k=4))


class KaraokeSession(Base):
    __tablename__ = "karaoke_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_id: Mapped[str] = mapped_column(
        String(4), nullable=True, unique=True
    )
    users: Mapped[list[KaraokeSessionUser]] = relationship()
    songs: Mapped[list[KaraokeSessionSong]] = relationship()

    def generate_display_id(self, session: Session):
        display_id = generate_id()
        all_sessions = session.query(KaraokeSession).all()
        all_display_ids = [ks.display_id for ks in all_sessions]
        while display_id in all_display_ids:
            display_id = generate_id()
        self.display_id = display_id

    def generate_song_queue(self, session: Session):
        user_ids = [user.user_id for user in self.users]
        result = session.execute(
            select(Song).where(
                Song.id.in_(
                    select(UserSongRating.song_id)
                    .select_from(UserSongRating)
                    .where(UserSongRating.user_id.in_(user_ids))
                )
            )
        )
        logger.info(result.all())

    # def get_next_song(self, session: Session):
    # self.songs.filter(played=False)
