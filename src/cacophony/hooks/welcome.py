import os.path


WELCOME_MESSAGE_KEY = 'welcome_message_files'


async def welcome(app, member):
    """Send a private message to a member to welcome him."""

    server_id = member.server.id
    try:
        message_path = app.conf[WELCOME_MESSAGE_KEY][server_id]
    except KeyError:
        app.warning("Configuration key %s/%s not set. Skipping.",
                    WELCOME_MESSAGE_KEY, member.server.id)
        return True  # Nothing else to do

    if message_path is None:
        return True  # Nothing to do, path not set in the config.

    if not os.path.exists(message_path):
        app.warning("Could not open file '%s': the file does not exist!",
                    message_path)
        return True

    with open(message_path) as stream:
        content = stream.read()
        app.info("Send welcome message to %s who joined %s!",
                 member.nick, member.server.name)
        await app.discord_client.send_message(member, content)


def load():
    return 'on_member_join', welcome
