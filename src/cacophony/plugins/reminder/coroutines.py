import asyncio
import datetime
import sqlalchemy


async def reminder(app):
    app.info("Reminder coroutine running.")
    while True:
        await asyncio.sleep(60)  # Sleep one minute
