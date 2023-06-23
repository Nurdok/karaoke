import click
from karaoke.playlist import *


@click.command()
@click.option("--user-id", "-u", type=int, help="User ID", multiple=True)
def start_session(user_id: list[int]) -> None:
    users: list[User] = []
    for uid in user_id:
        users.append(User.find_by_id(uid))

    session = Session.create(users=users)
    click.echo(f"Session created with ID {session.id}")


@click.command()
def list_users() -> None:
    all_users = User.get_all_users()
    click.echo(f"Found {len(all_users)} users:")
    for user in all_users:
        click.echo(f"{user.id}: {user.name}")


@click.command()
def add_user() -> None:
    name = click.prompt("Name")
    user = User.create(name)
    click.echo(f"User created with ID {user.id}")


@click.command()
def add_song() -> None:
    title = click.prompt("Title")
    artist = click.prompt("Artist")
    video_link = click.prompt("Video link")
    song = Song.create(
        title=title,
        artist=artist,
        video_link=video_link,
    )
    click.echo(f"Song created with ID {song.id}")


@click.command()
def list_songs() -> None:
    all_songs = Song.get_all_songs()
    click.echo(f"Found {len(all_songs)} songs:")
    for song in all_songs:
        click.echo(
            f"{song.id}: {click.style(song.title, bold=True)} by {song.artist}"
        )


@click.group()
def cli() -> None:
    pass


@click.group()
def users() -> None:
    pass


@click.group()
def songs() -> None:
    pass


@click.group()
def sessions() -> None:
    pass


cli.add_command(users, name="users")
users.add_command(list_users, name="list")
users.add_command(add_user, name="add")

cli.add_command(songs, name="songs")
songs.add_command(add_song, name="add")
songs.add_command(list_songs, name="list")

cli.add_command(sessions, name="sessions")
sessions.add_command(start_session, name="start")


if __name__ == "__main__":
    cli()
