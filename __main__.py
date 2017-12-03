import asyncio
import gbulb
from pandora import Client

gbulb.install()
loop = asyncio.get_event_loop()


def on_login(future):
    print(future.result())

client = Client()
asyncio.ensure_future(client.login('bob@bob.com', 'pass')).add_done_callback(on_login)

loop.run_forever()
