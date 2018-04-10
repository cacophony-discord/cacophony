from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, String

Model = declarative_base()


class Config(Model):
    """Describe a generic configuration setting for cacophony."""

    __tablename__ = "cacophony_config"

    server_id = Column(String, primary_key=True)
    name = Column(String, primary_key=True)
    value = Column(String)
