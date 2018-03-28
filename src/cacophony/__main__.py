"""Cacophony Discord Bot."""
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
def run(profile, *args, **kwargs):
    """Run the bot with the specified `profile`."""
    CacophonyApplication(name=profile).run()


if __name__ == "__main__":
    main()
