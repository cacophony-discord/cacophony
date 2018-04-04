import datetime
import re
import sqlalchemy
from .models import Remind


def decode_delay(delay):
    regex = re.compile(r'(\d+)([mhdw])')
    match = regex.match(delay)
    if match is None:
        return  # Invalid format

    number, descriptor = match.groups()
    number = int(number)
    if number <= 0:
        return  # Invalid number

    if descriptor == 'm':  # minutes
        delta = datetime.timedelta(minutes=number)
    elif descriptor == 'h':  # hours
        delta = datetime.timedelta(hours=number)
    elif descriptor == 'd':  # days
        delta = datetime.timedelta(days=number)
    elif descriptor == 'w':  # weeks
        delta = datetime.timedelta(weeks=number)
    else:
        delta = None  # Invalid descriptor
    return delta


async def on_remind(app, message, *args):
    """Manage the reminders.

    General usage:
        !remind [add|del|list] (options...)

    This command has several sub-commands.

    add: add a reminder.

    Usage:
        !remind add [time_descriptor] [description]

    Parameters:
        time_descriptor: the amount of time to wait for the bot before it
        notifies the channel about the reminder. Format is "[number][unit]"
        where number is a strictly positive number and unit is one of the
        following values:
            - m: minutes
            - h: hours
            - d: days
            - w: weeks
        description: the textual description of the reminder

    Examples:
        !remind add 3d Do a barrel roll
        The command above will register a reminder which will be notified by
        the bot after the next three days (3d)

        !remind add 1w Dungeon party
        The bot will wait a week before reminding on the channel about a
        dungeon party.

    Return:
        The bot should display a message with the ID, description and delay of
        the reminder which has just be created.


    del: delete a reminder

    Usage:
        !remind del [id]

    Parameters:
        id: the id of the reminder to delete. To successfully perform deletion
        of a reminder, the reminder has to belong to the right channel and
        the command performer must be the author of the reminder.

    Example:
        !remind del 1
        Delete reminder whose ID is 1.

    Return:
        A message from the bot to indicate whether the reminder has been
        successfully deleted or not.

    list: list the five upcoming reminders

    Usage:
        !remind list

    Return:
        A textual list of the five upcoming reminders, from the closest to the
        furthest. For each reminder is given the ID, description author and
        the amount of time.
    """
    sub_command, *arguments = args
    if sub_command == "add":
        await on_remind_add(app, message, *arguments)
    elif sub_command == "del":
        await on_remind_del(app, message, *arguments)
    elif sub_command == "list":
        await on_remind_list(app, message, *arguments)
    else:
        await app.discord_client.send_message(
            message.channel,
            "Unknown subcommand '{}' for !remind.".format(sub_command)
        )


async def on_remind_add(app, message, *arguments):
    """Add a reminder."""
    delay, *description = arguments
    session = app.create_database_session()

    delta = decode_delay(delay)

    if delta is None:
        await app.discord_client.send_message(
            message.channel,
            "_Invalid delay format '{}'. Could not add reminder._".format(
                delay))
        return

    reminder_datetime = datetime.datetime.now() + delta
    remind = Remind(server_id=message.server.id,
                    channel_id=message.channel.id,
                    author_id=message.author.id,
                    reminder_datetime=reminder_datetime,
                    description=' '.join(description))
    session.add(remind)
    session.commit()

    await app.discord_client.send_message(
        message.channel,
        ('_Added reminder **{}** **"{}"** which '
         'will be fired {}_'.format(remind.id, remind.description,
                                    remind.remaining_time())))
    session.close()


async def on_remind_del(app, message, *arguments):
    """Delete a reminder."""
    reminder_id, *_ = arguments
    try:
        reminder_id = int(reminder_id)
        if reminder_id <= 0:
            raise ValueError
    except ValueError:
        await app.discord_client.send_message(
            message.channel,
            ("_Invalid reminder ID **{}**. "
             "Must be a strictly positive number._'".format(reminder_id)))
        return

    session = app.create_database_session()
    remind = session.query(Remind).filter_by(
        id=reminder_id, channel_id=message.channel.id,
        server_id=message.server.id,
        author_id=message.author.id).first()
    if remind is None:
        await app.discord_client.send_message(
            message.channel,
            ("_Could not find reminder of yours "
             "with ID **{}** on this server._").format(reminder_id))
        return

    session.delete(remind)
    await app.discord_client.send_message(
        message.channel,
        ("_Successfully deleted reminder **{}**._".format(reminder_id)))
    session.commit()
    session.close()


async def on_remind_list(app, message, *arguments):
    """List the five upcoming reminders."""
    session = app.create_database_session()
    reminds = session.query(Remind).filter_by(
        server_id=message.server.id
    ).order_by(
        sqlalchemy.desc(Remind.reminder_datetime)
    ).limit(5).all()

    if reminds is None or len(reminds) == 0:
        await app.discord_client.send_message(
            message.channel,
            ("_There are currently no reminders at the moment._"))
        return

    output = "**5 last upcoming reminders:**\n"
    server_members = {int(m.id): m.name for m in message.server.members}
    for remind in reminds:
        output += "- ID:{} **{}** by **{} {}**\n".format(
            remind.id, remind.description,
            server_members.get(remind.author_id, '_Unknown_'),
            remind.remaining_time())
    await app.discord_client.send_message(message.channel, output)
    session.close()


def load():
    return '!remind', on_remind
