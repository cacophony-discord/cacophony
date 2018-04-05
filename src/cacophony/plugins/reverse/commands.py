"""Plugin commands."""

async def on_reverse(app, channel, *args):
    """Reverse the string in argument and send it to `channel`."""
    if not args:
        await app.send_message(channel,
                               f"_Usage: {app.prefixize('remind')} string_")
    else:
        await app.send_message(channel, ' '.join(args)[::-1])
