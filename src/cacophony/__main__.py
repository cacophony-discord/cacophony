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
@click.option('--plugins')
def main(action, profile, plugins):
    """Instanciate an application, then run it."""

    if plugins:
        plugin_list = plugins.split(',')
    else:
        plugin_list = []
    handler = _HANDLERS.get(action)
    if handler is not None:
        handler(profile, plugins=plugin_list)


@handle('run')
def run(profile: str, plugins: list, *args, **kwargs) -> None:
    """Run the bot with the specified `profile`."""
    discord_token = os.environ.get('CACOPHONY_DISCORD_TOKEN')
    if discord_token is None:
        click.secho("You must set the environment variable "
                    "'CACOPHONY_DISCORD_TOKEN' before running the bot.",
                    fg='red', err=True)
        raise SystemExit(-1)
    db_path = os.environ.get('CACOPHONY_DATABASE', 'sqlite://')
    application = CacophonyApplication(discord_token,
                                       name=profile, db_path=db_path,
                                       plugins=plugins)
    application.run()


if __name__ == "__main__":
    main()
