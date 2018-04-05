from sqlalchemy import Column, Integer
from cacophony import models


class RoulettePlayer(models.Model):
    __tablename__ = "cacophony_roulette_player"

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer)
    player_id = Column(Integer)
    score = Column(Integer)
