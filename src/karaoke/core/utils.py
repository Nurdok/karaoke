from typing import Optional

from sqlalchemy.orm import Session

from karaoke.core.song import Song
from karaoke.core.rating import UserSongRating
from karaoke.core.session import KaraokeSession, KaraokeSessionUser


def get_any_unrated_song(user_id: int, session: Session) -> Optional[Song]:
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


def create_karaoke_session(
    user_ids: list[int], session: Session
) -> KaraokeSession:
    karaoke_session = KaraokeSession()
    karaoke_session.generate_display_id(session)
    session.add(karaoke_session)
    session.commit()

    for uid in user_ids:
        session_user = KaraokeSessionUser(
            karaoke_session_id=karaoke_session.id, user_id=uid
        )
        session.add(session_user)

    session.commit()
    karaoke_session.generate_song_queue(session)
    session.commit()
    return karaoke_session
