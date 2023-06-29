from sqlalchemy.orm import Session

from karaoke.core.song import Song
from karaoke.core.rating import UserSongRating


def get_any_unrated_song(user_id: int, session: Session):
    return (
        session.query(Song)
        .outerjoin(
            user_ratings := (
                session.query(UserSongRating)
                .filter_by(user_id=user_id)
                .subquery()
            )
        )
        .filter(user_ratings.c.song_id.is_(None))
        .first()
    )
