from sqlalchemy import Column, Integer
from .base import Base


class RoulettePlayer(Base):
    __tablename__ = "cacophony_roulette_player"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer)
    player_id = Column(Integer)
    score = Column(Integer)
