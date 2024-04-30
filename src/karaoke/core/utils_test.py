from pytest import fixture
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from karaoke.core.base import Base
from karaoke.core.user import User
from karaoke.core.song import Song


@fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_get_next_unrated_song(session: Session) -> None:
    session.add_all(
        users := [
            amir := User(name="Amir"),
            haim := User(name="Haim"),
            daniel := User(name="Daniel"),
        ]
    )

    session.add_all(
        songs := [
            song1 := Song(title="song1"),
            song2 := Song(title="song2"),
            song3 := Song(title="song3"),
            song4 := Song(title="song4"),
        ]
    )

    session.commit()
