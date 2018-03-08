"""Cacophony Discord Bot."""
import click

from .app import CacophonyApplication


@click.command()
@click.argument('name')
def main(name='cacophony'):
    """Instanciate an application, then run it."""
    application = CacophonyApplication(name=name)
    application.run()


if __name__ == "__main__":
    main()
