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
@click.option("--session-id", "-s", type=str, help="Session ID")
def next_song(session_id: str) -> None:
    session = Session.find_by_id(session_id)
    song = session.get_next_song()
    if song is None:
        click.echo("No more songs in the queue.")
        return
    click.echo(f"Next song: {song.title} by {song.artist}")


@click.command()
def list_users() -> None:
    all_users = User.get_all_users()
    click.echo(f"Found {len(all_users)} users:")
    for user in all_users:
        click.echo(f"{user.id}: {user.name}")


@click.command()
def show_user() -> None:
    user_id = click.prompt("User ID", type=int)
    user = User.find_by_id(user_id)
    click.echo(f"User {user.id}: {user.name}")
    for song_rating in user.song_ratings:
        click.echo(f"\t{song_rating.song.title}: {song_rating.rating.name}")


@click.command()
def add_user() -> None:
    name = click.prompt("Name")
    user = User.create(name)
    click.echo(f"User created with ID {user.id}")


@click.command()
@click.option("--user-id", "-u", type=int, help="User ID")
def rate_song(user_id: int) -> None:
    user = User.find_by_id(user_id)

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

    all_songs = Song.get_all_songs()
    rated_songs = [sr.song for sr in user.song_ratings]
    for song in all_songs:
        if song in rated_songs:
            continue
        click.echo(
            f"How well do you know the song "
            f"{click.style(song.title, bold=True)} by "
            f"{click.style(song.artist, bold=True)}?"
        )
        for score, rating in sorted(ratings.items()):
            click.echo(f"{score}: {rating_names[rating]}")
        score = click.prompt("Score", type=int)
        user.rate_song(song, rating=ratings[score])
        click.echo()

    click.echo("All songs rated!")


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
users.add_command(rate_song, name="rate")
users.add_command(show_user, name="show")

cli.add_command(songs, name="songs")
songs.add_command(add_song, name="add")
songs.add_command(list_songs, name="list")

cli.add_command(sessions, name="sessions")
sessions.add_command(start_session, name="start")
sessions.add_command(next_song, name="next")


if __name__ == "__main__":
    cli()
