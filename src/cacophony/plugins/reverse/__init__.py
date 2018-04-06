"""reverse plugin.

Export a command that lets someone reverse a string.

"""
from .commands import on_reverse


commands = {
    'reverse': [on_reverse],
}
