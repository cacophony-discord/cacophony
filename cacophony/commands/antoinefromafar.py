import requests

from acapela_group.base import AcapelaGroup, AcapelaGroupError


async def on_antoinefromafar(self, message, *args):
    """Say something with 'AntoineFromAfar' voice on the voice channel."""
    text_to_say = self.bots[message.server.id].brain.generate()

    try:
        mp3_url = AcapelaGroup().get_mp3_url('sonid15',
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
