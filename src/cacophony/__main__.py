"""Cacophony Discord Bot."""
import click

from .app import CacophonyApplication


@click.command()
@click.argument('name')
def main(name='cacophony'):
    """Instanciate an application, then run it."""
    app = CacophonyApplication(name=name)
    app.run()


if __name__ == "__main__":
    main()
