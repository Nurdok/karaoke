import click
from karaoke.playlist import *


@click.command()
@click.option("--user-id", "-u", type=int, help="User ID", multiple=True)
def start_session(user_ids: list[int]) -> None:
    users: list[User] = []
    for user_id in user_ids:
        users.append(User.get_user(user_id))

    session = Session.create(users=users)
    click.echo(f"Session created with ID {session.id}")


@click.command()
def list_users() -> None:
    all_users = User.get_all_users()
    for user in all_users:
        click.echo(f"{user.id}: {user.name}")


if __name__ == "__main__":
    list_users()
