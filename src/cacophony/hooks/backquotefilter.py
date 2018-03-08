async def backquotefilter(app, answer):
    """Prevent the bot from sending any answer if there is an URL in it."""
    if '```' in answer:
        app.warning("Detected backquotes. Won't answer.")
        return False
    else:
        return True


def load():
    return 'on_answer', backquotefilter
