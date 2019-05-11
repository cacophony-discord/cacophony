#!/usr/bin/env python3

import asyncio

from .base import Application, Hook, Plugin
from .models import Model, Config
from .web import load_web_app

from collections import defaultdict
import discord
import importlib
import sqlalchemy


class CacophonyApplication(Application):
    """Application class."""

    def __init__(self, discord_token, name='cacophony', db_path='sqlite://',
                 plugins=None, *args, **kwargs):

        if plugins is None:
            self._plugin_names = []
        else:
            self._plugin_names = plugins

        self.discord_client = None  # Discord link
        self._discord_token = discord_token
        self.loop = None  # asyncio loop
        self.bots = {}  # Key is discord server, value is bot instance

        # Database related attributes:
        self._db = None  # Cacophony relational database
        self._db_session_maker = None  # Session maker to the database
        self._db_session = None

        # Bot related attributes:
        self.hooks = {}
        self.callbacks = {}
        self.messages_queue = None
        self.is_running = True

        # Task handling the coroutine to process discord messages from a queue.
        self.process_messages_task = None

        # Loaded plugins:
        self._plugins = defaultdict(str)
        self._plugins_coroutines = []
        self._commands_handlers = defaultdict(list)
        self._hooks = defaultdict(list)
        self._command_prefix = None

        super().__init__(name=name, *args, **kwargs)
        self._configure_bot()
        self._init_database(db_path)

    @property
    def db_session(self):
        """Get the database session."""
        return self._db_session

    @property
    def plugins(self) -> defaultdict(str):
        """Get the loaded plugins."""
        return self._plugins

    @property
    def servers(self):
        """Get the discord servers the bot is connected to. If the bot is
        not connected yet, then this property should not be used."""
        return self.discord_client.servers

    async def _load_plugins(self):
        """Private. Load plugins referenced in the configuration.

        The plugins must be located in cacophony.plugins submodule.

        """
        for plugin in self._plugin_names:
            self.info("Load plugin '%s'.", plugin)
            try:
                module = importlib.import_module(f".plugins.{plugin}",
                                                 package="cacophony")
            except ModuleNotFoundError as exn:
                self.error("Could not load plugin '%s': '%s'",
                           plugin, exn)
            else:

                # Instantiate the plugin
                if hasattr(module, 'plugin_class'):
                    self._plugins[plugin] = module.plugin_class(self)
                else:
                    self._plugins[plugin] = Plugin(self)

                # Call the plugin 'on_load' hook
                await self._plugins[plugin].on_load()

                if hasattr(module, 'coroutines'):
                    self._schedule_module_coroutines(module)
                if hasattr(module, 'commands'):
                    self._add_command_handlers(module)
                if hasattr(module, 'hooks'):
                    self._register_hooks(module)

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

    def _register_hooks(self, module):
        """Private. Register hooks exported by `module`.

        Each module can export, for each existing event, a list of hooks
        to be called upon trigerred event. For a complete list of supported
        hooks, see base.py.

        Args:
            module: The module to register the hooks from.

        """
        for hook_type, handlers in module.hooks.items():
            self.info("Register hooks for event '%s'", hook_type.name)
            self._hooks[hook_type] += handlers

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

    def _init_database(self, db_path: str) -> None:
        """Private. Initialize the database whose path is `db_path`.

        Args:
            db_path: sqlalchemy path to the database.

        """
        self._db = sqlalchemy.create_engine(db_path)
        Model.metadata.create_all(self._db)
        self._db_session_maker = sqlalchemy.orm.sessionmaker()
        self._db_session_maker.configure(bind=self._db)
        self._db_session = self._db_session_maker()

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

    def unprefixize(self, command_name):
        """Unprefixize `command_name` by removing its prefix.

        Args:
            command_name: The command name to remove the prefix from.

        Example:
            If the command name is "!say" and the prefix is "!", then the
                method will return "say".

        Returns:
            The unprefixized, real command name.

        """
        return command_name.lstrip(self._command_prefix)

    def get_config(self, server_id: str, setting: str, default=None) -> str:
        """Get the `setting` value for `server_id`.

        The setting will be fetched into the database. If it cannot be found,
        then the method will return `default` instead.

        Args:
            server_id: The discord's server id to fetch the setting from.
            setting: The setting to fetch the value from.

        Returns:
            The setting value.

        """
        try:
            config = self.db_session.query(Config).filter_by(
                server_id=server_id,
                name=setting).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return default
        else:
            return config.value

    def set_config(self, server_id: str, setting: str, value: str) -> None:
        """Set `setting`'s `value` whose server's identified by `server_id`.

        Args:
            server_id: The discord's server id to fetch the setting from.
            setting: The setting to set a value to.
            value: The value to set.

        """
        config = self.db_session.query(Config).filter_by(
            server_id=server_id,
            name=setting).one()
        if config is None:
            config = Config(server_id=server_id, name=setting, value=value)
            self._db_session.add(config)
        else:
            config.value = value
        self._db_session.commit()

    async def on_ready(self):
        self.info("Cacophony bot ready.")

        # Notify plugins that the server is ready.
        for plugin in self._plugins.values():
            await plugin.on_ready()

        await self.discord_client.change_presence(
            status=discord.Game(name="Type !help for more information."))

    def _is_command_allowed(self,
                            server_id: str,
                            channel: str,
                            command: str) -> bool:
        """Private. Check whether `command` can be executed or not.

        This function is called once `command` has been summoned on discord
        whose server id is `server_id` and channel is `channel`.

        Args:
            server_id: The id from the discord server where the command has
                been summoned.
            channel: The channel where the discord channel has been summoned.
            command: The command that has been summoned.

        Returns:
            True if the command can be executed, False otherwise.

        """
        # XXX: Redefine permissions/configuration
        return command in self._commands_handlers

    async def on_message(self, message):
        self.info("%s %s %s: %s", message.server, message.channel,
                  message.author, message.content)

        message_content = message.content

        # Discard every messages sent by the bot itself.
        if message.author.id == self.discord_client.user.id:
            self.info("Do not handle self messages.")
            return  # Do not handle self messages

        # XXX: How to handle private messages properly? Type attribute maybe.
        try:
            server_id = message.server.id
        except AttributeError:
            server_id = ''

        # Discard every messages sent by the bot itself.
        if message.author.id == self.discord_client.user.id:
            self.info("Do not handle self messages.")
            return  # Do not handle self messages

        for hook in self._hooks[Hook.ON_MESSAGE]:
            await hook(self, message)

        if message_content.startswith(self._command_prefix):
            command, *args = message.content.split(' ')
            command = self.unprefixize(command)
            if self._is_command_allowed(server_id,
                                        message.channel.name,
                                        command):
                # Call every registered command handlers
                for handler in self._commands_handlers[command]:
                    await handler(self, message, *args)

    async def on_member_join(self, member):
        self.info("%s joined the server '%s'!",
                  member.nick, member.server.name)

    async def on_server_join(self, server):
        """Call hooks registered upon new server joining."""
        for hook in self._hooks[Hook.ON_SERVER_JOIN]:
            await hook(self, server)

    def register_discord_callbacks(self):
        """Hack to register discord callbacks."""
        self.discord_client.on_ready = self.on_ready
        self.discord_client.on_message = self.on_message
        self.discord_client.on_member_join = self.on_member_join
        self.discord_client.on_server_join = self.on_server_join

        # And register generic command callbacks
        self._commands_handlers['ping'] += [on_ping]
        self._commands_handlers['help'] += [on_help]
        self._commands_handlers['vjoin'] += [on_vjoin]
        self._commands_handlers['vquit'] += [on_vquit]

    async def process_messages(self):
        """Process messages to send by checking `self.messages_queue`."""
        self.info("process_messages() coroutine started!")
        while True:
            channel, message = await self.messages_queue.get()
            try:
                await self.discord_client.send_message(channel, message)
            except discord.DiscordException as exn:
                self.warning("Error while attempting to send message %s to %s:"
                             " Caught exception %s.", channel, message, exn)
            else:
                self.debug("Sent message '%s' for channel '%s'", channel,
                           message)
            finally:
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
        self.debug("Enqueue message %s for %s", message, target)
        await self.messages_queue.put((target, message,))

    async def _async_run(self):
        await self._load_plugins()
        self.info(self.conf)
        while self.is_running:
            try:
                self.discord_client = discord.Client()
                self.messages_queue = asyncio.Queue(loop=self.loop)
                self.process_messages_task = \
                    asyncio.ensure_future(self.process_messages(),
                                          loop=self.loop)
                self.register_discord_callbacks()
                await self.discord_client.start(self._discord_token)
            except KeyboardInterrupt:
                self.info("Caught ^C signal.")
                self.process_messages_task.cancel()
                self.loop.run_until_complete(self.discord_client.logout())
                self.is_running = False
            except Exception as exn:
                self.info("Caught %s %s", type(exn), str(exn))
            finally:
                self.info("Terminating...")

    def run(self):
        self.loop = asyncio.get_event_loop()
        webapp = load_web_app()
        webapp_handler = webapp.make_handler()
        web_coro = self.loop.create_server(webapp_handler, '0.0.0.0', 8080)
        srv = self.loop.run_until_complete(web_coro)
        self.loop.run_until_complete(self._async_run())
        self.loop.run_until_complete(webapp_handler.finish_connections(1.0))
        srv.close()
        self.loop.run_until_complete(srv.wait_closed())
        self.loop.run_until_complete(webapp.finish())
        self.loop.close()
        raise SystemExit(0)


async def on_ping(self, message, *args):
    """Ping the bot that will answer with a 'Pong!' message."""
    await self.send_message(message.channel, '_Pong!_')


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
    if args:
        sub_command, *_ = args
        if sub_command in self._commands_handlers:
            callback = self._commands_handlers[sub_command][0]
        else:
            callback = None

        sub_command = self.prefixize(sub_command)
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
        for command, callbacks in self._commands_handlers.items():
            summary_doc, *_ = callbacks[0].__doc__.split('\n\n')
            output += f"**{self.prefixize(command)}**: {summary_doc}\n"
        output += ("\nFor further help on any command,"
                   " type !help _command_ (Exemple: !help ping)\n\n")

        client_id = self.discord_client.user.id
        output += ("Feel free to invite me on your server(s): "
                   "https://discordapp.com/oauth2/authorize?"
                   f"client_id={client_id}&scope=bot&permissions=0\n"
                   "Follow my development on "
                   "https://github.com/cacophony-discord/cacophony")
        await self.send_message(message.author, output)
