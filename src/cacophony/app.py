#!/usr/bin/env python3

import asyncio

from .base import Application, Cacophony
from .models import Model
from chattymarkov import ChattyMarkov

from collections import defaultdict
import discord
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
        self.messages_queue = None
        self.is_running = True

        # Task handling the coroutine to process discord messages from a queue.
        self.process_messages_task = None
        self._plugins_coroutines = []
        self._commands_handlers = defaultdict(list)
        self._command_prefix = None

        super().__init__(name=name, *args, **kwargs)
        self._configure_bot()
        self._load_plugins()
        self._init_cacophony_database()

    @property
    def database(self):
        return self._cacophony_db

    def _load_plugins(self):
        """Private. Load plugins referenced in the configuration.

        The plugins must be located in cacophony.plugins submodule.

        """
        plugins = self.conf.get('plugins', [])
        for plugin in plugins:
            self.info("Load plugin '%s'.", plugin)
            try:
                module = importlib.import_module(f".plugins.{plugin}",
                                                 package="cacophony")
            except ModuleNotFoundError as exn:
                self.error("Could not load plugin '%s': '%s'",
                           plugin, exn)
            else:
                if hasattr(module, 'coroutines'):
                    self._schedule_module_coroutines(module)
                if hasattr(module, 'commands'):
                    self._add_command_handlers(module)

    def _schedule_module_coroutines(self, module):
        """Private. Schedule coroutines listed in `module`.

        The `module` object has an attribute named `coroutines` that should be
        a set of coroutines to schedule to the main loop.

        Args:
            module: The module to schedule the coroutines from.

        """
        for coro in module.coroutines:
            self.info("Schedule coroutine %s", coro.__name__)
            asyncio.ensure_future(coro(self), loop=self.loop)

    def _add_command_handlers(self, module):
        """Private. Add command handlers from `module`.

        The `module` object should have an attribute whose name is `commands`.
        This attribute should be a dictionary whose keys are strings
        referring to the commands without prefix, and whose values should be
        sets of handlers to call upon command execution.

        There can be several handlers for the command. The priority call for
        those handlers are described as plugin loading order, then handler
        order in the dictionary's values.

        Args:
            module: The module to load the commands from.

        """
        for command, handlers in module.commands.items():
            self.info("Add handlers for '%s'", command)
            self._commands_handlers[command] += handlers

    def _cancel_plugins_coroutines(self):
        """Private. Cancel coroutines loaded through plugins.

        The coroutines loaded through plugins are stored in the
        `_plugins_coroutines` instance member. Those are actually tasks
        that will be cancelled.

        """
        for task in self._plugins_coroutines:
            self.debug("Cancel task '%s'.", task)
            task.cancel()

    def _configure_bot(self):
        """Private. Set main configuration for the bot."""
        self._command_prefix = self.conf.get('command_prefix', '!')


    def create_database_session(self):
        if self._session_maker is None:
            return  # cannot create session
        return self._session_maker()

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
            Model.metadata.create_all(self._cacophony_db)
            self._session_maker = sqlalchemy.orm.sessionmaker()
            self._session_maker.configure(bind=self._cacophony_db)

    def prefixize(self, command_name: str) -> str:
        """Prefixize `command_name` with the command prefix.
        
        Args:
            command_name: The command name to prefix.

        Example:
            If the command name is "say" and the prefix is "!", then the
            method will return "!say".

        Returns:
            The prefixized command name.

        """
        return f'{self._command_prefix}{command_name}'

    def build_brain(self, brain_string):
        return ChattyMarkov(brain_string)

    def command_config(self, server_id, command):
        """Return the configuration associated for `command` on `server_id`."""
        return self.conf['servers'][server_id]['commands'][command]

    def get_hook_config(self, server_id, hook):
        """Return the configuration associated for `hook` on `server_id`."""
        return self.conf['servers'][server_id]['hooks'][hook]

    async def on_ready(self):
        self.info("Ready to roll!")
        self.info("Servers are:")
        discord_servers = self.conf.get('servers', [])
        for server in self.discord_client.servers:

            self.info("- %s (ID: %s)", server, server.id)
            if server.id not in discord_servers:
                self.warning("No server ID '%s' in config. Skipping.",
                             server.id)
                continue

            # Build the brain for the server
            brain = self.build_brain(
                discord_servers[server.id]['brain_string'])
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
            hooks = discord_servers[server.id].get('hooks', {})
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
            hook_config = self.get_hook_config(server_id, hook)
            hooked_channels = hook_config.get('_channels', ['*'])
            # hookee represents the action being hooked (e.g. 'on_message')
            hookee, hook = module.load()
            loaded_hooks[hookee].append((hook, hooked_channels))
        self.hooks[server_id] = loaded_hooks

    def _is_command_allowed(self, server_id, channel, command):
        """Check wether a command can be executed on some channel."""
        if (command, '*') in self.callbacks:
            return True  # Generic commands are always allowed

        # Strip the '!'
        command = command[1:]
        try:
            channels = self.conf['servers'][server_id][
                    'commands'][command]['_channels']
        except KeyError as exn:
            self.warning("KeyError caught in is_command_allowed: %s",
                         str(exn))
            return False
        else:
            return '*' in channels or channel in channels

    async def on_message(self, message):
        self.info("%s %s %s: %s", message.server, message.channel,
                  message.author, message.content)

        message_content = message.content

        # How to handle private messages properly? Type attribute maybe.
        try:
            server_id = message.server.id
        except AttributeError:
            return

        # Discard every messages sent by the bot itself.
        if message.author.id == self.discord_client.user.id:
            self.info("Do not handle self messages.")
            return  # Do not handle self messages

        if message.channel.name.startswith('Direct'):
            return  # No direct messages.

        # Call hooks if any
        hooks = self.hooks.get(server_id, {})
        for (hook, channels) in hooks.get('on_message', {}):
            if '*' not in channels and message.channel.name not in channels:
                continue  # Hook not configured for this channel
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

        servers = self.conf.get('servers', {})
        if server_id not in servers:
            return  # Server not found in config

        server_info = servers[server_id]

        bot = self.bots.get(server_id, None)
        if bot is None:
            self.warning("Bot instance is 'None'")
            return  # Nothing to do

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
            for (hook, channels) in self.hooks[server_id]['on_answer']:
                if '*' not in channels and \
                        message.channel.name not in channels:
                    continue  # Hook not configured for this channel
                if await hook(self, answer):
                    continue  # The hook returned True. Continue
                else:
                    return  # The hook return False. Do nothing else.
            await self.send_message(message.channel, answer)

    async def on_member_join(self, member):
        self.info("%s joined the server '%s'!",
                  member.nick, member.server.name)
        server_id = member.server.id

        # Call hooks if any
        for hook, channels in self.hooks[server_id]['on_member_join']:
            if await hook(self, member):
                continue  # The hook returned True. Continue
            else:
                return  # The hook return False. Do nothing else.

    def _load_opus(self):
        if not discord.opus.is_loaded():
            discord.opus.load_opus("libopus.so")

    def register_discord_callbacks(self):
        """Hack to register discord callbacks."""
        self.discord_client.on_ready = self.on_ready
        self.discord_client.on_message = self.on_message
        self.discord_client.on_member_join = self.on_member_join

        # And register generic command callbacks
        self.callbacks[('!ping', '*')] = on_ping
        self.callbacks[('!say', '*')] = on_say
        self.callbacks[('!help', '*')] = on_help
        self.callbacks[('!mute', '*')] = on_mute
        self.callbacks[('!vjoin', '*')] = on_vjoin
        self.callbacks[('!vquit', '*')] = on_vquit

    async def process_messages(self):
        """Process messages to send by checking `self.messages_queue`."""
        self.info("process_messages() coroutine started!")
        while True:
            channel, message = await self.messages_queue.get()
            await self.discord_client.send_message(channel, message)
            self.messages_queue.task_done()

    async def send_message(self,
                           target,
                           message: str) -> None:
        """Send `message` to `channel`.

        This method will just enqueue a tuple (`channel`, `message`) in the
        messages to be sent.

        Args:
            target: The target to send the message to. It can be either a
                discord channel or a discord user.
            message: The message to send.
        """
        await self.messages_queue.put((target, message,))

    def run(self):
        self._load_opus()
        self.info(self.conf)
        while self.is_running:
            try:
                self.discord_client = discord.Client()
                self.loop = asyncio.get_event_loop()
                self.messages_queue = asyncio.Queue(loop=self.loop)
                self.process_messages_task = \
                    asyncio.ensure_future(self.process_messages(),
                                          loop=self.loop)

                token = self.conf.get('token', '')
                if token:
                    self.debug("Will log using token '%s'", token)
                else:
                    self.critical("Error: no token found in configuration. "
                                  "Exiting...")
                    raise SystemExit(-1)
                self.register_discord_callbacks()

                self.loop.run_until_complete(self.discord_client.start(token))
            except KeyboardInterrupt:
                self.info("Caught ^C signal.")
                self.process_messages_task.cancel()
                self.loop.run_until_complete(self.discord_client.logout())
                self.is_running = False
            except Exception as exn:
                self.info("Caught %s %s", type(exn), str(exn))
            finally:
                self.info("Terminating...")
        self.loop.close()
        raise SystemExit(0)


async def on_ping(self, message, *args):
    """Ping the bot that will answer with a 'Pong!' message."""
    await self.send_message(message.channel, '_Pong!_')


async def on_say(self, message, *args):
    """Simply say what's needed to be said."""
    try:
        bot = self.bots[message.server.id]
    except KeyError:
        self.logger.info("Unknown bot for server %s", message.server.id)
    else:
        if not bot.is_mute:
            await self.send_message(message.channel, ' '.join(args))


async def on_vjoin(self, message, *args):
    """Join the vocal channel the author command is in.

    In order to work succesfully, the command sender must be connected
    to some discord vocal channel.
    """
    voice_channel = message.author.voice.voice_channel
    self.debug("Voice channel is %s", voice_channel)
    if voice_channel is not None:
        # Join the channel the user is in
        await self.discord_client.join_voice_channel(voice_channel)
        await self.send_message(message.channel,
                                f"_Joined {voice_channel}._")
    else:
        await self.send_message(
            message.channel,
            "_You must be in a voice channel so I can catch up with you._")


async def on_vquit(self, message, *args):
    """Quit the vocal channel the bot is on."""
    if self.discord_client.is_voice_connected(message.server):
        self.debug("Will disconnect from vocal in %s", message.server)
        voice_client = self.discord_client.voice_client_in(message.server)
        voice_channel = voice_client.channel
        await voice_client.disconnect()
        await self.send_message(
            message.channel,
            f"_Successfully disconnected from {voice_channel}_")


async def on_mute(self, message, *args):
    """Mute/unmute the bot."""

    bot = self.bots[message.server.id]
    if bot.is_mute:
        bot.unmute()
        await self.send_message(message.channel,
                                "_The bot is now unmute!_")
    else:
        bot.mute()
        await self.send_message(message.channel,
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
            await self.send_message(
                message.author,
                (f"_Unknown command {sub_command}_. Type !help "
                 "for more information."))
            return

        await self.send_message(
            message.author,
            f"**{sub_command}**\n\n```{callback.__doc__}```")
    else:
        output = "**Available commands:**\n\n"
        for ((command, server), cb) in self.callbacks.items():
            if server != '*' and message.server.id != server:
                continue
            summary_doc, *_ = cb.__doc__.split('\n\n')
            output += f"**{command}**: {summary_doc}\n"
        output += ("\nFor further help on any command,"
                   " type !help _command_ (Exemple: !help anim)")
        await self.send_message(message.author, output)
