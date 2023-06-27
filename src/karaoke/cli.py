import click

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from karaoke.core.user import User
from karaoke.core.song import Song
from karaoke.core.rating import UserSongRating, Rating
from karaoke.core.session import Session, SessionSong, SessionUser
from karaoke.core.base import Base


LOCAL_DB = "sqlite:///karaoke.sqlite"


def format_song(song: Song) -> str:
    return (
        f"{click.style(song.title, bold=True)} by "
        f"{click.style(song.artist, bold=True)}"
    )


@click.command()
def _init_db() -> None:
    engine = create_engine(LOCAL_DB, echo=True)
    Base.metadata.create_all(engine)
    click.echo("Initialized database.")


@click.command()
def _create_user() -> None:
    engine = create_engine(LOCAL_DB, echo=True)
    with sessionmaker(bind=engine)() as session:
        name = click.prompt("Name")
        user = User(name=name)
        session.add(user)
        session.commit()
        click.echo(f"User created with ID {user.id}")


@click.group()
def _cli() -> None:
    pass


@click.group()
def _db() -> None:
    pass


@click.group()
def _user() -> None:
    pass


_cli.add_command(_db, name="db")
_db.add_command(_init_db, name="init")

_cli.add_command(_user, name="user")
_user.add_command(_create_user, name="create")


if __name__ == "__main__":
    _cli()
