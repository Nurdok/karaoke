from typing import Optional

import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from karaoke.core.user import User
from karaoke.core.song import Song
from karaoke.core.rating import UserSongRating, Rating
from karaoke.core.session import (
    KaraokeSession,
    KaraokeSessionSong,
    KaraokeSessionUser,
)
from karaoke.core.base import Base
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

LOCAL_DB = "sqlite:///karaoke.sqlite"
ECHO = False


def format_song(song: Song) -> str:
    return (
        f"{click.style(song.title, bold=True)} by "
        f"{click.style(song.artist, bold=True)}"
    )


@click.command()
def _init_db() -> None:
    engine = create_engine(LOCAL_DB, echo=ECHO)
    Base.metadata.create_all(engine)
    click.echo("Initialized database.")


@click.command()
@click.option("--name", "-n", type=str, help="Name")
def _create_user(name: Optional[str]) -> None:
    engine = create_engine(LOCAL_DB, echo=ECHO)
    with sessionmaker(bind=engine)() as session:
        if name is None:
            name = click.prompt("Name")
        user = User(name=name)
        session.add(user)
        session.commit()
        click.echo(f"User created with ID {user.id}")


@click.command()
def _list_users() -> None:
    engine = create_engine(LOCAL_DB, echo=ECHO)
    with sessionmaker(bind=engine)() as session:
        all_users = session.query(User).all()
        click.echo(f"Found {len(all_users)} users:")
        for user in all_users:
            click.echo(f"{user.id}: {user.name}")


@click.command()
@click.option("--user-id", "-u", type=int, help="User ID")
def _rate_song(user_id: int) -> None:
    engine = create_engine(LOCAL_DB, echo=True)
    with sessionmaker(bind=engine)() as session:
        user: Optional[User] = (
            session.query(User).filter_by(id=user_id).first()
        )
        if user is None:
            click.echo(f"User with ID {user_id} not found.")
            return

        ratings: dict[int, Rating] = {
            0: Rating.DONT_KNOW,
            1: Rating.SING_ALONG,
            2: Rating.CAN_TAKE_THE_MIC,
            3: Rating.NEED_THE_MIC,
        }
        rating_names: dict[Rating, str] = {
            Rating.DONT_KNOW: "I don't know the song",
            Rating.SING_ALONG: "I can sing along",
            Rating.CAN_TAKE_THE_MIC: "I can take the mic",
            Rating.NEED_THE_MIC: "I NEED the mic!",
        }

        print(
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

        while (
            unrated_song := session.query(Song)
            .outerjoin(
                user_ratings := (
                    session.query(UserSongRating)
                    .filter_by(user_id=user_id)
                    .subquery()
                )
            )
            .filter(user_ratings.c.song_id.is_(None))
            .first()
        ) is not None:
            click.echo(f"How well do you know this song?")
            click.echo(format_song(unrated_song))
            click.echo()
            for score, rating in sorted(ratings.items()):
                click.echo(f"{score}: {rating_names[rating]}")
            score = click.prompt("Score", type=int)
            user_song_rating = UserSongRating(
                user_id=user.id, song_id=unrated_song.id, rating=ratings[score]
            )
            session.add(user_song_rating)
            session.commit()
            click.echo()


@click.command()
@click.option("--title", "-t", type=str, help="Title")
@click.option("--artist", "-a", type=str, help="Artist")
@click.option("--video-link", "-l", type=str, help="Video Link")
def _create_song(title, artist, video_link) -> None:
    engine = create_engine(LOCAL_DB, echo=ECHO)
    with sessionmaker(bind=engine)() as session:
        if title is None:
            title = click.prompt("Title")
        if artist is None:
            artist = click.prompt("Artist")
        if video_link is None:
            video_link = click.prompt("Video Link")
        song = Song(title=title, artist=artist, video_link=video_link)
        session.add(song)
        session.commit()
        click.echo(f"Song created with ID {song.id}")


@click.command()
def _list_songs() -> None:
    engine = create_engine(LOCAL_DB, echo=ECHO)
    with sessionmaker(bind=engine)() as session:
        all_songs = session.query(Song).all()
        click.echo(f"Found {len(all_songs)} songs:")
        for song in all_songs:
            click.echo(f"{song.id}: {format_song(song)}")


@click.command()
@click.option("--user-id", "-u", type=int, help="User ID", multiple=True)
def _create_session(user_id: list[int]) -> None:
    engine = create_engine(LOCAL_DB, echo=ECHO)
    with sessionmaker(bind=engine)() as session:
        karaoke_session = KaraokeSession()
        karaoke_session.generate_display_id(session)
        session.add(karaoke_session)
        session.commit()

        for uid in user_id:
            session_user = KaraokeSessionUser(
                karaoke_session_id=karaoke_session.id, user_id=uid
            )
            session.add(session_user)

        session.commit()
        karaoke_session.generate_song_queue(session)
        click.echo(f"Session created with ID {karaoke_session.display_id}")


@click.command()
@click.option("--session-id", "-s", type=str, help="Session ID")
def next_song(session_id: str) -> None:
    engine = create_engine(LOCAL_DB, echo=ECHO)
    with sessionmaker(bind=engine)() as session:
        karaoke_session = (
            session.query(KaraokeSession).filter(display_id=session_id).first()
        )
        if karaoke_session is None:
            click.echo("Session not found")
            return

        song: Optional[Song] = karaoke_session.get_next_song()
        if song is None:
            click.echo("No more songs in the queue.")
            return
        click.echo(f"Next song: {format_song(song)}")


@click.group()
def _cli() -> None:
    pass


@click.group()
def _db() -> None:
    pass


@click.group()
def _user() -> None:
    pass


@click.group()
def _song() -> None:
    pass


@click.group()
def _session() -> None:
    pass


_cli.add_command(_db, name="db")
_db.add_command(_init_db, name="init")

_cli.add_command(_user, name="user")
_user.add_command(_create_user, name="create")
_user.add_command(_list_users, name="list")
_user.add_command(_rate_song, name="rate")

_cli.add_command(_song, name="song")
_song.add_command(_create_song, name="create")
_song.add_command(_list_songs, name="list")

_cli.add_command(_session, name="session")
_session.add_command(_create_session, name="create")


def main():
    _cli()


if __name__ == "__main__":
    main()
