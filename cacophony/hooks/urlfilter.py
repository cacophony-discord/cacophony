import re

URL_REGEX = re.compile(r'https?://')


async def urlfilter(app, answer):
    """Prevent the bot from sending any answer if there is an URL in it."""
    if URL_REGEX.match(answer):
        return False
    else:
        return True


def load():
    return 'on_answer', urlfilter
