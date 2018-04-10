"""Cacophony Discord Bot."""
import os
from pathlib import Path

import click

from .app import CacophonyApplication
from .base import ProfileNotFoundError


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
    try:
        discord_token = os.environ.get('CACOPHONY_DISCORD_TOKEN')
        if discord_token is None:
            click.secho("You must set the environment variable "
                        "'CACOPHONY_DISCORD_TOKEN' before running the bot.",
                        fg='red', err=True)
            raise SystemExit(-1)
        db_path = os.environ.get('CACOPHONY_DATABASE', 'sqlite://')
        application = CacophonyApplication(discord_token,
                                           name=profile, db_path=db_path)
    except ProfileNotFoundError as exn:
        click.secho(f'[!] {exn}', fg='red', err=True)
    else:
        application.run()


@handle('create')
def create(profile: str, *args, **kwargs) -> None:
    """Create the profile named `profile` for cacophony.

    The function will create a directory named after `profile` under the
    tree ~/.config/cacophony-discord and create a config.yml file into it.


    Args:
        profile: The profile name to create.

    """
    base_dir = Path.home() / ".config" / "cacophony-discord" / profile
    if not base_dir.exists():
        click.secho(f"[*] Creating {base_dir}.", fg='green', err=True)
        Path.mkdir(base_dir, parents=True)
    else:
        click.secho(f"[!] Profile '{profile}' already exists.", fg="red",
                    err=True)
        return

    config_path = base_dir / 'config.yml'
    default_content = (
        "discord:\n"
        "    token: YOUR_TOKEN_HERE\n")
    with open(config_path, "w") as stream:
        n = stream.write(default_content)
        click.secho(f"[*] Written {n} bytes in 'config.yml'", fg='green',
                    err=True)
    click.secho("[*] Profile creation successful. Replace the token in your "
                "config.yml file and try launching the bot through "
                f"'cacophony run --profile {profile}'", fg='green', err=True)


if __name__ == "__main__":
    main()
