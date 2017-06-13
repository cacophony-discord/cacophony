import datetime
from sqlalchemy import Column, DateTime, Integer, String
from .base import Base


class Remind(Base):
    __tablename__ = "cacophony_remind"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer)
    channel_id = Column(Integer)
    author_id = Column(Integer)
    reminder_datetime = Column(DateTime)
    description = Column(String)

    def __repr__(self):
        return ("<Remind(id='{}', server_id='{}', author_id='{}', "
                "reminder_datetime='{}', description='{}'>".format(
                    self.id, self.server_id, self.author_id,
                    self.reminder_datetime, self.description))

    def remaining_time(self):
        now = datetime.datetime.now()
        if now > self.reminder_datetime:
            return  # reminder alreasy passed
        delta = self.reminder_datetime - now
        if delta.days > 7:
            weeks = delta.days // 7
            return "in {} week{}".format(
                weeks, "s" if weeks > 1 else "")
        elif delta.days > 0:
            return "in {} day{}".format(
                delta.days, "s" if delta.days > 1 else "")
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return "in {} hour{}".format(
                hours, "s" if hours > 1 else "")
        elif delta.seconds > 60:
            minutes = delta.minutes // 60
            return "in {} minute{}".format(
                minutes, "s" if minutes > 1 else "")
        else:
            return "soon"
