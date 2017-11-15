#!/usr/bin/env python3

import asyncio
from bsol.app import Application

from cacophony import Cacophony
from cacophony.models.base import Base as BaseModel
from chattymarkov import ChattyMarkov
from chattymarkov.database.redis import RedisDatabase

from collections import defaultdict
import discord
import click
import importlib
import random
import sqlalchemy


class CacophonyApplication(Application):
    """Application class."""

    def __init__(self, name='cacophony', *args, **kwargs):
        self.discord_client = None  # Discord link
        self.loop = None  # asyncio loop
        self.bots = {}  # Key is discord server, value is bot instance
        self._cacophony_db = None  # Cacophony relational database
        self._session_maker = None  # Session maker to the database
        self.hooks = {}
        self.callbacks = {}
        super().__init__(name=name, *args, **kwargs)
        self._init_cacophony_database()

    @property
    def database(self):
        return self._cacophony_db

    def create_database_session(self):
        if self._session_maker is None:
            return  # cannot create session
        return self._session_maker()

    def _check_discord_config(self):
        if 'discord' not in self.conf and \
                'email' not in self.conf['discord'] and \
                'password' not in self.conf['discord']:
            self.error("Please configure your discord credentials.")
            raise SystemExit(-1)

    def _init_cacophony_database(self):
        if 'databases' in self.conf:
            db_config = self.conf['databases'].get('cacophony_database')
            self.info("%s", db_config)
            if db_config is None:
                return  # No database
        else:
            return  # No database, skip.

        # Again, I should consider using a factory pattern here. X(
        if db_config.get('type', '') == 'SQLITE_FILE':
            self._cacophony_db = sqlalchemy.create_engine(
                'sqlite:///{}'.format(db_config.get('path', ':memory:')))
            BaseModel.metadata.create_all(self._cacophony_db)
            self._session_maker = sqlalchemy.orm.sessionmaker()
            self._session_maker.configure(bind=self._cacophony_db)

    def build_brain(self, name):
        if name not in self.conf['databases']:
            self.warning("There is no database named '%s'. "
                         "Skip brain building.")
            return
        database_info = self.conf['databases'][name]

        database = None
        # Consider using factory pattern next time.
        if database_info['type'] == "REDIS_UNIX_SOCKET":
            database = RedisDatabase(
                unix_socket_path=database_info['unix_socket_path'],
                db=database_info['db'])

        if database is None:
            self.error("Unknown database type '%s'! Skip brain building.")
            return
        return ChattyMarkov(database)

    async def on_ready(self):
        self.info("Ready to roll!")
        self.info("Servers are:")
        discord_servers = self.conf['discord']['servers']
        for server in self.discord_client.servers:

            self.info("- %s (ID: %s)", server, server.id)
            if server.id not in discord_servers:
                self.warning("No server ID '%s' in config. Skipping.",
                             server.id)
                continue

            # Build the brain for the server
            brain = self.build_brain(discord_servers[server.id]['brain'])
            if brain:
                chattyness = discord_servers[server.id].get('chattyness',
                                                            0.1)
                channels = discord_servers[server.id].get('chatty_channels')
                self.bots[server.id] = Cacophony(
                    logger=self.logger,
                    name=discord_servers[server.id]['nickname'],
                    markov_brain=brain, chattyness=chattyness,
                    channels=channels)
            else:
                self.warning("Could not find brain for server '%s'!",
                             server)

            # Load extra-commands if any
            extra_commands = discord_servers[server.id].get('commands', {})
            if len(extra_commands) > 0:
                self._load_extra_commands(server.id, extra_commands)

            # Schedule jobs if any
            self._schedule_jobs(server, discord_servers[server.id])

            # Load hooks if any
            hooks = discord_servers[server.id].get('hooks', [])
            self._load_hooks(server.id, hooks)

        await self.discord_client.change_presence(
                game=discord.Game(name="Type !help for more information."))

    def _schedule_jobs(self, server, server_config):
        """Load some specific coroutine jobs described in config."""
        jobs = server_config.get("jobs", list())
        for job in jobs:
            module = importlib.import_module(".jobs.{}".format(job),
                                             package="cacophony")
            coroutine = module.load()
            self.info("Loaded job '%s'", job)
            channels = [channel for channel in server.channels
                        if channel.name in server_config.get(
                            'channels', list())]
            self.info("Channels are: %s", channels)
            for channel in channels:
                self.info("Schedule job %s for %s:%s", job,
                          server.name, channel.name)
                asyncio.ensure_future(coroutine(self, channel), loop=self.loop)

    def _load_extra_commands(self, server_id, extra_commands):
        """Load extra commands."""
        for command, config in extra_commands.items():
            self.info("Will load %s", command)
            module = importlib.import_module(".commands.{}".format(command),
                                             package="cacophony")
            command, function = module.load()
            self.callbacks[(command, server_id)] = function

    def _load_hooks(self, server_id, hooks):
        """Load hooks for a specific server."""
        self.info("Will load hooks.")
        loaded_hooks = defaultdict(list)
        for hook in hooks:
            self.info("Load hook '%s' for server id '%s'", hook, server_id)
            module = importlib.import_module(".hooks.{}".format(hook),
                                             package="cacophony")
            # hookee represents the action being hooked (e.g. 'on_message')
            hookee, hook = module.load()
            loaded_hooks[hookee].append(hook)
        self.hooks[server_id] = loaded_hooks

    def _is_command_allowed(self, server_id, channel, command):
        """Check wether a command can be executed on some channel."""
        if (command, '*') in self.callbacks:
            return True  # Generic commands are always allowed

        # Strip the '!'
        command = command[1:]
        try:
            channels = self.conf['discord']['servers'][server_id][
                    'commands'][command]['_channels']
        except KeyError as exn:
            self.warning("KeyError caught in is_command_allowed: %s",
                         str(exn))
            return False
        else:
            if '*' in channels or channel in channels:
                return True
            else:
                return False

    async def on_message(self, message):
        self.info("%s %s %s: %s", message.server, message.channel,
                  message.author, message.content)

        message_content = message.content

        # How to handle private messages properly? Type attribute maybe.
        try:
            server_id = message.server.id
        except AttributeError:
            return

        if server_id not in self.conf['discord']['servers']:
            return  # Server not found in config

        server_info = self.conf['discord']['servers'][server_id]

        if message.author.id == self.discord_client.user.id:
            self.info("Do not handle self messages.")
            return  # Do not handle self messages

        if message.channel.name.startswith('Direct'):
            return  # No direct messages.

        bot = self.bots.get(server_id, None)
        if bot is None:
            self.warning("Bot instance is 'None'")
            return  # Nothing to do

        # Call hooks if any
        for hook in self.hooks[server_id]['on_message']:
            if await hook(self, message):
                continue  # The hook returned True. Continue
            else:
                return  # The hook return False. Do nothing else.

        if message_content.startswith('!'):
            command, *args = message.content.split(' ')
            if not self._is_command_allowed(server_id,
                                            message.channel.name,
                                            command):
                return

            if (command, '*') in self.callbacks:
                await self.callbacks[(command, '*')](self, message, *args)
            elif (command, server_id) in self.callbacks:
                await self.callbacks[(command, server_id)](self,
                                                           message, *args)
            return

        # Learn what has been told
        bot.brain.learn(message_content)

        if bot.is_mute:
            self.warning("Bot is mute!")
            return  # Nothing to answer

        if message.channel.name not in bot.channels:
            self.warning("Not allowed to answer in this channel! "
                         "Allowed channels are %s", bot.channels)
            return  # Not allowed to speak on this channel

        local_nickname = server_info["nickname"]
        mentioned = local_nickname.lower() in message_content.lower() or \
            self.discord_client.user in message.mentions

        will_answer = random.random() < bot.chattyness or mentioned

        if will_answer:
            self.info("Will answer.")
            answer = bot.brain.generate()
            if mentioned:
                answer = "<@{}> {}".format(message.author.id,
                                           answer)
            # Call hooks if any
            for hook in self.hooks[server_id]['on_answer']:
                if await hook(self, answer):
                    continue  # The hook returned True. Continue
                else:
                    return  # The hook return False. Do nothing else.
            await self.discord_client.send_message(message.channel,
                                                   answer)

    async def on_member_join(self, member):
        self.info("%s joined the server '%s'!",
                  member.nick, member.server.name)
        server_id = member.server.id
        # Call hooks if any
        for hook in self.hooks[server_id]['on_member_join']:
            if await hook(self, member):
                continue  # The hook returned True. Continue
            else:
                return  # The hook return False. Do nothing else.

    def register_discord_callbacks(self):
        """Hack to register discord callbacks."""
        self.discord_client.on_ready = self.on_ready
        self.discord_client.on_message = self.on_message
        self.discord_client.on_member_join = self.on_member_join

        # And register generic command callbacks
        self.callbacks[('!ping', '*')] = on_ping
        self.callbacks[('!help', '*')] = on_help
        self.callbacks[('!mute', '*')] = on_mute

    def run(self):
        self.info(self.conf)
        self.discord_client = discord.Client()
        self.loop = asyncio.get_event_loop()
        discord_conf = self.conf.get('discord')
        if discord_conf is None:
            self.error("Discord configuration is absent. Quitting...")
            raise SystemExit(-1)

        token = discord_conf.get('token')
        if token is not None:
            start_args = [token]
            self.debug("Will log using token '%s'", token)
        else:
            start_args = [discord_conf.get('email'),
                          discord_conf.get('password')]

            self.debug("Will log with %s:%s", self.conf['discord']['email'],
                       self.conf['discord']['password'])

        self.register_discord_callbacks()
        is_running = True
        while is_running:
            try:
                self.info("Args are: %s", start_args)
                self.loop.run_until_complete(
                    self.discord_client.start(*start_args))
            except KeyboardInterrupt:
                self.info("Caught ^C signal.")
                self.loop.run_until_complete(self.discord_client.logout())
                is_running = False
            except Exception as exn:
                self.info("Caught %s %s", type(exn), str(exn))
            finally:
                self.info("Terminating...")
        self.loop.close()
        raise SystemExit(0)


async def on_ping(self, message, *args):
    """Ping the bot that will answer with a 'Pong!' message."""
    await self.discord_client.send_message(message.channel,
                                           '_Pong!_')


async def on_mute(self, message, *args):
    """Mute/unmute the bot."""

    try:
        god = self.conf['discord']['god']
        bot = self.bots[message.server.id]
    except KeyError:
        self.warning("There is not bot instance for server '%s' nor "
                     "configured god!",
                     message.server.id)
    else:
        if message.author.id != god:
            self.warning("Don't have permission to mute/unmute the god!")
            return

        if bot.is_mute:
            bot.unmute()
            await self.discord_client.send_message(message.channel,
                                                   "_The bot is now unmute!_")
        else:
            bot.mute()
            await self.discord_client.send_message(message.channel,
                                                   "_The bot is now mute!_")


async def on_help(self, message, *args):
    """Display the list of available commands by private message."""
    if len(args) > 0:
        sub_command, *_ = args
        sub_command = "!" + sub_command
        if (sub_command, '*') in self.callbacks:
            callback = self.callbacks.get((sub_command, '*'))
        elif (sub_command, message.server.id) in self.callbacks:
            callback = self.callbacks.get(
                (sub_command, message.server.id))
        else:
            callback = None

        if callback is None:
            await self.discord_client.send_message(
                message.author,
                ("_Unknown command {}_. Type !help "
                 "for more information.".format(sub_command)))
            return

        await self.discord_client.send_message(
            message.author,
            "**{}**\n\n```{}```".format(sub_command, callback.__doc__))
    else:
        output = "**Available commands:**\n\n"
        for ((command, server), cb) in self.callbacks.items():
            if server != '*' and message.server.id != server:
                continue
            summary_doc, *_ = cb.__doc__.split('\n\n')
            output += "**{}**: {}\n".format(command, summary_doc)
        output += ("\nFor further help on any command,"
                   " type !help _command_ (Exemple: !help anim)")
        await self.discord_client.send_message(message.author, output)


@click.command()
@click.argument('name')
def run(name='cacophony'):
    """Instanciate an application, then run it."""
    app = CacophonyApplication(name=name)
    app.run()


if __name__ == "__main__":
    run()
