import logging

from karaoke.core.song import Song
from karaoke.core.user import User
from karaoke.core.base import Base
from karaoke.core.rating import UserSongRating, Rating
from karaoke.core.utils import create_karaoke_session
from karaoke.core.session import (
    KaraokeSession,
    KaraokeSessionSong,
    KaraokeSessionUser,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from unittest.mock import patch, MagicMock
from pytest import fixture


@fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_get_next_song(session: Session) -> None:
    users: list[User] = [
        amir := User(name="Amir"),
        haim := User(name="Haim"),
        daniel := User(name="Daniel"),
        twaik := User(name="Twaik"),
    ]

    session.add_all(users)
    session.commit()

    songs: list[Song] = [
        Song(
            title="Non-stop",
            artist="Cast of Hamilton",
            video_link="https://www.youtube.com/watch?v=6_35a7sn6ds",
        ),
        Song(
            title="My Shot",
            artist="Cast of Hamilton",
            video_link="https://www.youtube.com/watch?v=PEHKBckBODQ",
        ),
        Song(
            title="Unicorn",
            artist="Noa Kirel",
            video_link="https://www.youtube.com/watch?v=6_35a7sn6ds",
        ),
        Song(
            title="Weird Korean song",
            artist="Korean guy",
            video_link="https://www.youtube.com/watch?v=PEHKBckBODQ",
        ),
        Song(
            title="Seven Rings",
            artist="Ariana Grande",
            video_link="https://www.youtube.com/watch?v=RubBzkZzpUA",
        ),
        Song(
            title="Started from the Bottom",
            artist="Drake",
            video_link="https://www.youtube.com/watch?v=RubBzkZzpUA",
        ),
    ]

    session.add_all(songs)
    session.commit()

    amir.ratings = [
        UserSongRating(song_id=songs[0].id, rating=Rating.NEED_THE_MIC),
        UserSongRating(song_id=songs[1].id, rating=Rating.NEED_THE_MIC),
        UserSongRating(song_id=songs[2].id, rating=Rating.SING_ALONG),
        UserSongRating(song_id=songs[3].id, rating=Rating.DONT_KNOW),
        UserSongRating(song_id=songs[4].id, rating=Rating.DONT_KNOW),
        UserSongRating(song_id=songs[5].id, rating=Rating.SING_ALONG),
    ]

    haim.ratings = [
        UserSongRating(song_id=songs[0].id, rating=Rating.SING_ALONG),
        UserSongRating(song_id=songs[1].id, rating=Rating.SING_ALONG),
        UserSongRating(song_id=songs[2].id, rating=Rating.CAN_TAKE_THE_MIC),
        UserSongRating(song_id=songs[3].id, rating=Rating.SING_ALONG),
        UserSongRating(song_id=songs[4].id, rating=Rating.NEED_THE_MIC),
        UserSongRating(song_id=songs[5].id, rating=Rating.SING_ALONG),
    ]

    daniel.ratings = [
        UserSongRating(song_id=songs[0].id, rating=Rating.SING_ALONG),
        UserSongRating(song_id=songs[1].id, rating=Rating.CAN_TAKE_THE_MIC),
        UserSongRating(song_id=songs[2].id, rating=Rating.CAN_TAKE_THE_MIC),
        UserSongRating(song_id=songs[3].id, rating=Rating.DONT_KNOW),
        UserSongRating(song_id=songs[4].id, rating=Rating.CAN_TAKE_THE_MIC),
        UserSongRating(song_id=songs[5].id, rating=Rating.NEED_THE_MIC),
    ]

    twaik.ratings = [
        UserSongRating(song_id=songs[0].id, rating=Rating.SING_ALONG),
        UserSongRating(song_id=songs[1].id, rating=Rating.SING_ALONG),
        UserSongRating(song_id=songs[2].id, rating=Rating.CAN_TAKE_THE_MIC),
        UserSongRating(song_id=songs[3].id, rating=Rating.NEED_THE_MIC),
        UserSongRating(song_id=songs[4].id, rating=Rating.CAN_TAKE_THE_MIC),
        UserSongRating(song_id=songs[5].id, rating=Rating.DONT_KNOW),
    ]

    session.commit()

    karaoke_session: KaraokeSession = create_karaoke_session(
        user_ids=[user.id for user in users],
        session=session,
    )

    playlist: list[Song] = []
    while (song := karaoke_session.get_next_song(session=session)) is not None:
        print(song)
        playlist.append(song)
        karaoke_session.mark_current_song_as_played(session=session)

    assert playlist == [
        songs[1],
        songs[4],
        songs[3],
        songs[0],
        songs[5],
        songs[2],
    ]


def rate_song(
    user: User, song: Song, rating: Rating, *, session: Session
) -> UserSongRating:
    user_song_rating: UserSongRating = UserSongRating(
        user_id=user.id,
        song_id=song.id,
        rating=rating,
    )
    session.add(user_song_rating)
    session.commit()
    return user_song_rating


def test_session_song_queue(session: Session) -> None:
    """Test that the session initial song queue is generated correctly."""

    # set up the data
    users: list[User] = [
        user1 := User(name="user1"),
        user2 := User(name="user2"),
        user3 := User(name="user3"),
    ]

    session.add_all(users)
    session.commit()

    songs: list[Song] = [
        song1 := Song(title="song1", artist="artist1", video_link="link1"),
        song2 := Song(title="song2", artist="artist2", video_link="link2"),
        song3 := Song(title="song3", artist="artist3", video_link="link3"),
    ]

    session.add_all(songs)
    session.commit()

    # Multiple users can sing song1, so it should be included.
    rate_song(user1, song1, Rating.NEED_THE_MIC, session=session)
    rate_song(user2, song1, Rating.CAN_TAKE_THE_MIC, session=session)

    # Only one user can sing song2, so it should not be included.
    # User3 can sing this song, but they aren't part of the session.
    rate_song(user1, song2, Rating.NEED_THE_MIC, session=session)
    rate_song(user3, song2, Rating.CAN_TAKE_THE_MIC, session=session)

    # Two users know song3, but no one can take the mic,
    # so it should not be included.
    rate_song(user1, song3, Rating.SING_ALONG, session=session)
    rate_song(user2, song3, Rating.SING_ALONG, session=session)

    karaoke_session: KaraokeSession = create_karaoke_session(
        [user1.id, user2.id], session=session
    )

    assert set(song.song_id for song in karaoke_session.songs) == {song1.id}
