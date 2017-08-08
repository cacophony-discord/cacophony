"""Chattymarkov base code for database submodule."""


class AbstractDatabase:
    """AbstractDatabase class."""

    def __init__(self, *args, **kwargs):
        pass

    def add(self, key, element):
        """Add an entry into the database."""

    def random(self, key):
        """Pick up a random entry from the `key` subset into the database."""

    def get(self, key, default=None):
        """Get the value associated to `key` into the database."""

    def set(self, key, value):
        """Set `value` to `key` in database."""
