"""Cacophony Discord Bot."""
import os
from pathlib import Path

import click

from .app import CacophonyApplication


_HANDLERS = {}


def handle(action):
    """Register a function handler for a given action."""
    def wrap(function):
        _HANDLERS[action] = function
        return function
    return wrap


@click.command()
@click.argument('action')
@click.option('--profile')
def main(action, profile):
    """Instanciate an application, then run it."""

    handler = _HANDLERS.get(action)
    if handler is not None:
        handler(profile)


@handle('run')
def run(profile: str, *args, **kwargs) -> None:
    """Run the bot with the specified `profile`."""
    discord_token = os.environ.get('CACOPHONY_DISCORD_TOKEN')
    if discord_token is None:
        click.secho("You must set the environment variable "
                    "'CACOPHONY_DISCORD_TOKEN' before running the bot.",
                    fg='red', err=True)
        raise SystemExit(-1)
    db_path = os.environ.get('CACOPHONY_DATABASE', 'sqlite://')
    application = CacophonyApplication(discord_token,
                                       name=profile, db_path=db_path)
    application.run()


if __name__ == "__main__":
    main()
