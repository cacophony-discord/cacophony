import re
import requests


from acapela_group.base import AcapelaGroup, AcapelaGroupError

_MENTION_REGEX = re.compile(r'<@([0-9]+)>')


def mention_clean(server):
    members = {str(member.id): member.nick for member in server.members}

    def re_callback(match):
        id = match.group(1)
        return members[id]

    return re_callback


async def on_antoinefromafar(self, message, *args):
    """Say something with 'AntoineFromAfar' voice on the voice channel."""
    text_to_say = _MENTION_REGEX.sub(
        mention_clean(message.server),
        self.bots[message.server.id].brain.generate())

    conf = self.command_config(message.server.id, 'antoinefromafar')
    username = conf.get('username')
    password = conf.get('password')
    try:
        acapela = AcapelaGroup()
        if username is not None and password is not None:
            self.debug("Will authenticate with %s:%s", username, password)
        mp3_url = acapela.get_mp3_url('sonid15',
                                      'AntoineFromAfar (emotive voice)',
                                      text_to_say)
    except AcapelaGroupError as err:
        self.warning("Could not get MP3 URL: %s", str(err))
    else:
        if self.discord_client.is_voice_connected(message.server):
            voice_client = self.discord_client.voice_client_in(message.server)
            self.debug("MP3 url: %s", mp3_url)
            with open('/tmp/tmp.mp3', 'wb') as stream:
                stream.write(requests.get(mp3_url).content)

            voice = voice_client.create_ffmpeg_player('/tmp/tmp.mp3')
            voice.start()


def load():
    return '!antoinefromafar', on_antoinefromafar
