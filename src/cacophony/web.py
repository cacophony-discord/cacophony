from aiohttp import web


async def hello(request):
    return web.Response(body=b"Bot is running!",
                        headers={'Content-Type': 'text/html'})


def load_web_app():
    app = web.Application()
    app.router.add_route('GET', '/', hello)
    return app
