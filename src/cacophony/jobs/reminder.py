import asyncio
import datetime
import sqlalchemy

from ..models.remind import Remind


async def reminder(app, channel):
    """Notify recorder reminds for the given `channel`."""
    session = app.create_database_session()

    while True:
        app.debug("Check reminders for channel ID %s", channel.id)
        reminds = session.query(Remind).filter_by(
            server_id=channel.server.id,
            channel_id=channel.id
        ).order_by(sqlalchemy.desc(Remind.reminder_datetime)).all()

        for remind in reminds:
            if datetime.datetime.now() > remind.reminder_datetime:
                await app.discord_client.send_message(
                    channel,
                    '@here **Reminder:** {}'.format(remind.description))
                session.delete(remind)
        session.commit()
        await asyncio.sleep(60)  # Sleep one minute


def load():
    """Load the reminder coroutine."""
    return reminder
