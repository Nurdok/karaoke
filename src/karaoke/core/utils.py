from typing import Optional

from sqlalchemy.orm import Session

from karaoke.core.song import Song
from karaoke.core.rating import UserSongRating
from karaoke.core.session import KaraokeSession, KaraokeSessionUser


def get_overall_rating(song: Song, session: Session) -> int:
    print(f"Calculating overall rating for {song.title}")
    score: int = 0
    ratings = session.query(UserSongRating).filter_by(song_id=song.id).all()
    print(f"Found {len(ratings)} ratings for {song.title} ({song.id})")
    for rating in ratings:
        print(
            f"Rating by user {rating.user_id}: {rating.rating} ({KaraokeSession.get_rating_score(rating.rating)})"
        )
        score += KaraokeSession.get_rating_score(rating.rating)
        print(f"Accumulated score: {score}")
    return score


def get_any_unrated_song(user_id: int, session: Session) -> Optional[Song]:
    songs = (
        session.query(Song)
        .outerjoin(
            user_ratings := (
                session.query(UserSongRating)
                .filter_by(user_id=user_id)
                .subquery()
            )
        )
        .filter(user_ratings.c.song_id.is_(None))
        .all()
    )

    return max(
        songs, key=lambda song: get_overall_rating(song, session), default=None
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
