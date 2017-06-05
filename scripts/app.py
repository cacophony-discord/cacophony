#!/usr/bin/env python3

import asyncio
import aiohttp
from bsol.app import Application

from cacophony import Cacophony, CacophonyDispatcher
from chattymarkov import ChattyMarkov
from chattymarkov.database.redis import RedisDatabase

import discord
import json
import random

import urllib.parse


class CacophonyApplication(Application, CacophonyDispatcher):
    """Application class."""

    def __init__(self, *args, **kwargs):
        self.discord_client = None  # Discord link
        self.loop = None  # asyncio loop
        self.bots = {}  # Key is discord server, value is bot instance
        super().__init__(name='cacophony', *args, **kwargs)

    def _check_discord_config(self):
        if 'discord' not in self.conf and \
                'email' not in self.conf['discord'] and \
                'password' not in self.conf['discord']:
            self.error("Please configure your discord credentials.")
            raise SystemExit(-1)

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
                self.warning("No server ID '%s' in config. Skipping.")
                continue

            # Build the brain for the server
            brain = self.build_brain(discord_servers[server.id]['brain'])
            if brain:
                chattyness = discord_servers[server.id].get('chattyness',
                                                            0.1)
                channels = discord_servers[server.id].get('channels')
                self.bots[server.id] = Cacophony(
                    logger=self.logger,
                    name=discord_servers[server.id]['nickname'],
                    markov_brain=brain, chattyness=chattyness,
                    channels=channels)
            else:
                self.warning("Could not find brain for server '%s'!",
                             server)

    @CacophonyDispatcher.register('!help')
    async def on_help(self, message, *args):
        """Display the list of available commands by private message."""
        output = "**Available commands:**\n\n"
        for command, cb in self.dispatcher.items():
            output += "**{}**: {}\n".format(command, cb.__doc__)
        await self.discord_client.send_message(message.author, output)

    @CacophonyDispatcher.register('!ping')
    async def on_ping(self, message, *args):
        """Ping the bot that will answer with a 'Pong!' message."""
        await self.discord_client.send_message(message.channel,
                                               '_Pong!_')

    @CacophonyDispatcher.register('!anim')
    async def on_anim(self, message, *args):
        """Reply with a random gif given the provided keyword."""
        tag = urllib.parse.quote_plus(' '.join(args))
        base_url = ('https://api.giphy.com/v1/gifs/random?tag={}&'
                    'api_key=dc6zaTOxFJmzC'.format(tag))
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url) as resp:
                json_content = json.loads(await resp.text())
                if 'data' in json_content and 'image_original_url' \
                        in json_content['data']:
                    answer = json_content['data']['image_original_url']
                else:
                    answer = '_No gif found for keyword "{}"_'.format(
                        ' '.join(args))
        await self.discord_client.send_message(message.channel, answer)

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

        if message_content.startswith('!') and \
                message.channel.name in bot.channels:
            command, *args = message.content.split(' ')
            if command in self.__callbacks__:
                await self.dispatch(command)(self, message, *args)
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
            await self.discord_client.send_message(message.channel,
                                                   answer)

    def register_discord_callbacks(self):
        """Hack to register discord callbacks."""
        self.discord_client.on_ready = self.on_ready
        self.discord_client.on_message = self.on_message

    def run(self):
        self.info(self.conf)
        self.discord_client = discord.Client()
        self.loop = asyncio.get_event_loop()
        self.debug("Will log with %s:%s", self.conf['discord']['email'],
                   self.conf['discord']['password'])

        self.register_discord_callbacks()
        try:
            self.loop.run_until_complete(
                self.discord_client.start(self.conf['discord']['email'],
                                          self.conf['discord']['password']))
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.discord_client.logout())
        finally:
            self.loop.close()
        raise SystemExit(0)


if __name__ == "__main__":
    CacophonyApplication().run()
