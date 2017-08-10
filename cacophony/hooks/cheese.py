"""Dummy hook."""


async def hook_cheese(app, message):
    """Check whether the message contains 'cheese'. Answer back if that is
    the case.
    """
    app.info("cheese hook called")
    if 'cheese' in message.content:
        await app.discord_client.send_message(message.channel,
                                              'Did you guy say ''cheese''?')
    return True  # Let the 'on_message' main hook continue


def load():
    """Load the hook."""
    return 'on_message', hook_cheese
