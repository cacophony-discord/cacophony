import aiohttp
import urllib
import json


async def on_anim(self, message, *args):
    """Reply with a random gif given the provided keyword."""
    if len(args) < 1:
        await self.discord_client.send_message(
            message.channel,
            "_Missing keyword. Type !help anim for more information._")
        return

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


def load():
    return '!anim', on_anim
