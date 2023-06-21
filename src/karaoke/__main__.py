import click
import redis
from karaoke.playlist import *

@click.command()
def start_session():
    click.echo("Starting session...")
    Session("ABCD", users)
