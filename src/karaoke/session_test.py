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
    engine = create_engine("sqlite:///:memory:", echo=True)
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
    while (song := karaoke_session.get_next_song(session)) is not None:
        print(song)
        playlist.append(song)

    assert playlist == [
        songs[1],
        songs[4],
        songs[3],
        songs[0],
        songs[5],
        songs[2],
    ]
