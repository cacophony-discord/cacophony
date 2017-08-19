from collections import defaultdict, deque
from cacophony.models.roulette import RoulettePlayer
import random
import sqlalchemy


ROULETTE_LENGTH = 6
ROULETTES = defaultdict(list)
SHOOTERS = defaultdict(dict)


async def _setup_roulette(server_id, channel_id):
    """Setup the roulette for a given server and channel."""
    ROULETTES[(server_id, channel_id)] = deque([0]*ROULETTE_LENGTH)

    # Place the bullet
    ROULETTES[(server_id, channel_id)][
        random.randint(0, ROULETTE_LENGTH - 1)] = 1
    SHOOTERS[(server_id, channel_id)] = defaultdict(int)


async def _update_score(session, server_id, player_id, bonus):
    """Update the score of a player for a given server and channel."""
    player = session.query(RoulettePlayer).filter_by(
            server_id=server_id,
            player_id=player_id).one_or_none()
    if player is None:
        # No player found? Create one.
        player = RoulettePlayer(
            server_id=server_id,
            player_id=player_id,
            score=bonus
        )
        session.add(player)
    else:
        player.score += bonus


async def _on_roulette_stats(app, message, roulette_length):
    """Display the statistics about the roulette
    (top score and current game).
    """
    server_members = {int(m.id): m.display_name
                      for m in message.server.members}
    session = app.create_database_session()
    top_players = session.query(RoulettePlayer).filter_by(
        server_id=message.server.id
    ).order_by(sqlalchemy.desc(RoulettePlayer.score)).limit(5).all()

    if len(top_players) == 0:
        output = "There are no top players at the moment.\n"
    else:
        output = "Top 5 players are:\n\n"
        for index, player in enumerate(top_players):
            output += "**{}**: {} ({} point{})\n".format(
                index+1, server_members[player.player_id], player.score,
                '' if player.score == 1 else 's')
    output += "\nRemaining chambers: {}".format(roulette_length)
    await app.discord_client.send_message(message.channel, output)
    session.close()


async def on_roulette(app, message, *args):
    """Russian roulette game.

    Usage: !roulette [stats]

    If the stats argument is provided, the the command will return the
    number of remaining bullets and the top 5 players.

    According to the remaining bullets, points are granted or removed from
    the score:

    * First bullet:  +1|-1
    * Second bullet: +2|-2
    * Third bullet:  +3|-3
    * Fourth bullet: +4|-4
    * Fifth bullet:  +5|-5
    * Sixth bullet:   0|0

    Score are linear. The more risks there are, greater is the reward/malus.
    """
    player_id = message.author.id
    server_id = message.server.id
    channel_id = message.channel.id

    server_members = {m.id: m.display_name for m in message.server.members}

    if (server_id, channel_id) not in ROULETTES:
        await _setup_roulette(server_id, channel_id)

    roulette = ROULETTES[(server_id, channel_id)]
    shooters = SHOOTERS[(server_id, channel_id)]

    if len(args) > 0 and args[0] == "stats":
        # Display stats
        await _on_roulette_stats(app, message, len(roulette))
        return

    chamber = roulette.popleft()
    if chamber == 1:
        # The player has been shot. Update his score and reset the roulette.
        session = app.create_database_session()
        player = session.query(RoulettePlayer).filter_by(
            server_id=server_id,
            player_id=player_id).one_or_none()
        if player is None:
            # No player? Create an entry
            player = RoulettePlayer(
                server_id=server_id,
                player_id=player_id,
                score=0
            )
            session.add(player)
        else:
            app.info("Update the player's score!")
            # Update the score of the shot player (malus)
            remaining_bullets = len(roulette)
            if remaining_bullets > 0:
                player.score -= (ROULETTE_LENGTH - remaining_bullets)
                player.score = max(0, player.score)

        # Grand bonus to the other players
        if len(shooters) > 0:
            del shooters[player_id]
            for player, bonus in shooters.items():
                await _update_score(session, server_id, player, bonus)

        answer = ("**{}** pulls the trigger... "
                  "*BOOM*! **HEADSHOT**!".format(server_members[player_id]))
        await app.discord_client.send_message(message.channel, answer)

        # Reset roulette and shooters
        await _setup_roulette(server_id, channel_id)
        session.commit()
        session.close()
    else:
        # Update the shooter
        shooters[player_id] = ROULETTE_LENGTH - len(roulette)
        answer = ("**{}** pulls the trigger... *Click!*".format(
            server_members[player_id]))
        await app.discord_client.send_message(message.channel, answer)


def load():
    return '!roulette', on_roulette
