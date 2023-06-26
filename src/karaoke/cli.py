import click

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from karaoke.user import User
from karaoke.song import Song
from karaoke.rating import UserSongRating, Rating
from karaoke.session import Session, SessionSong, SessionUser


def format_song(song: Song) -> str:
    return (
        f"{click.style(song.title, bold=True)} by "
        f"{click.style(song.artist, bold=True)}"
    )


@click.command()
def _create_user() -> None:
    engine = create_engine("sqlite://", echo=True)
    with Session(engine) as session:
        name = click.prompt("Name")
        user = User(name="name")
        session.add(user)
        session.commit()
        click.echo(f"User created with ID {user.id}")


@click.group()
def cli() -> None:
    pass


@click.group()
def user() -> None:
    pass


cli.add_command(user, name="user")
user.add_command(_create_user, name="create")


if __name__ == "__main__":
    cli()
