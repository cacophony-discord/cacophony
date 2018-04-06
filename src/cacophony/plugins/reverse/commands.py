"""Plugin commands."""

async def on_reverse(app, message, *args):
    """Reverse the string in argument and send it back."""
    if not args:
        await app.send_message(message.channel,
                               f"_Usage: {app.prefixize('reverse')} string_")
    else:
        await app.send_message(message.channel, ' '.join(args)[::-1])
