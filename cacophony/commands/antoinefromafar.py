import re

import aiofiles
import requests

from acapela_group.base import AcapelaGroupAsync, AcapelaGroupError

_MENTION_REGEX = re.compile(r'<@([0-9]+)>')
_URL_FILTER = re.compile(r'(https?://[^ ]+|www\.[^ ]+)')


def mention_clean(server):
    members = {str(member.id): member.nick for member in server.members}

    def re_callback(match):
        id = match.group(1)
        return members.get(id)

    return re_callback


def clean_message(msg):
    return _URL_FILTER.sub(msg, '')


def generate_best_message(brain):
    """Return the longest match amongst 50 generated messages."""
    sentences = sorted((_URL_FILTER.sub('', brain.generate())
                        for _ in range(50)),
                       key=len,
                       reverse=True)
    return sentences[0]


async def on_antoinefromafar(self, message, *args):
    """Say something with 'AntoineFromAfar' voice on the voice channel."""
    if len(args) >= 1:
        text_to_say = ' '.join(args)
    else:
        text_to_say = _MENTION_REGEX.sub(
            mention_clean(message.server),
            generate_best_message(self.bots[message.server.id].brain))

    conf = self.command_config(message.server.id, 'antoinefromafar')
    username = conf.get('username')
    password = conf.get('password')
    try:
        async with AcapelaGroupAsync() as acapela:
            if username is not None and password is not None:
                self.debug("Will authenticate with %s:%s", username, password)
                await acapela.authenticate(username, password)
            mp3_url = await acapela.get_mp3_url(
                'French (France)', 'AntoineFromAfar (emotive voice)',
                text_to_say)
    except AcapelaGroupError as err:
        self.warning("Could not get MP3 URL: %s", str(err))
    else:
        if self.discord_client.is_voice_connected(message.server):
            voice_client = self.discord_client.voice_client_in(
                message.server)
            self.debug("MP3 url: %s", mp3_url)
            async with aiofiles.open('/tmp/tmp.mp3', 'wb') as stream:
                await stream.write(requests.get(mp3_url).content)
                await stream.flush()

            voice = voice_client.create_ffmpeg_player('/tmp/tmp.mp3')
            voice.start()


def load():
    return '!antoinefromafar', on_antoinefromafar
