from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from sqlalchemy import String

from karaoke.core.base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from karaoke.core.rating import UserSongRating, Rating
    from karaoke.core.song import Song


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    ratings: Mapped[list["UserSongRating"]] = relationship(
        back_populates="user",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name})"

    def __str__(self) -> str:
        return self.name

    def rate_song(
        self, song: "Song", rating: "Rating", session: Session
    ) -> None:
        # Avoid circular import
        from karaoke.core.rating import UserSongRating, Rating

        # Delete any existing rating
        session.query(UserSongRating).filter_by(
            user_id=self.id, song_id=song.id
        ).delete()

        if rating != Rating.UNKNOWN:
            user_rating: UserSongRating = UserSongRating(
                user_id=self.id,
                song_id=song.id,
                rating=rating,
            )
            session.add(user_rating)
        session.commit()
